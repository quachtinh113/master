#ifndef __NOWTRADING_BASKETMANAGER_MQH__
#define __NOWTRADING_BASKETMANAGER_MQH__

#include <Trade/Trade.mqh>
#include <NowTrading/Types.mqh>
#include <NowTrading/Utils.mqh>

class NtBasketManager
  {
private:
   CTrade m_trade;
   string m_symbol;
   long m_magic;
   int m_deviation_points;
   int m_retry_count;

   bool RetryBuySell(const ENUM_NT_DIRECTION dir,const double lots,const string comment,const double safety_sl_price)
     {
      for(int i=0;i<m_retry_count;i++)
        {
         bool ok=false;
         if(dir==NT_DIR_BUY)
            ok=m_trade.Buy(lots,m_symbol,0.0,(safety_sl_price>0.0?safety_sl_price:0.0),0.0,comment);
         else if(dir==NT_DIR_SELL)
            ok=m_trade.Sell(lots,m_symbol,0.0,(safety_sl_price>0.0?safety_sl_price:0.0),0.0,comment);
         if(ok)
            return(true);
         const uint rc=m_trade.ResultRetcode();
         if(rc!=TRADE_RETCODE_REQUOTE && rc!=TRADE_RETCODE_PRICE_CHANGED && rc!=TRADE_RETCODE_REJECT && rc!=TRADE_RETCODE_SERVER_BUSY)
            break;
         Sleep(150);
        }
      return(false);
     }

public:
   void Init(const string symbol,const long magic,const int deviation_points,const int retry_count)
     {
      m_symbol=symbol;
      m_magic=magic;
      m_deviation_points=deviation_points;
      m_retry_count=retry_count;
      m_trade.SetExpertMagicNumber(m_magic);
      m_trade.SetDeviationInPoints(m_deviation_points);
     }

   long BuildBasketId() const
     {
      return((long)TimeLocal());
     }

   bool OpenInitialBasket(const long basket_id,const ENUM_NT_DIRECTION dir,const double base_lots_total,
                          const bool use_pending,const double pending_lots,const double pending_offset_pips,
                          const double safety_sl_pips)
     {
      const double each=NtNormalizeVolume(m_symbol,base_lots_total/2.0);
      const double pending=NtNormalizeVolume(m_symbol,pending_lots);
      const string comment=NtBuildBasketComment(basket_id,dir);

      const double bid=SymbolInfoDouble(m_symbol,SYMBOL_BID);
      const double ask=SymbolInfoDouble(m_symbol,SYMBOL_ASK);
      const double pip=NtPipSize(m_symbol);
      double sl=0.0;
      if(safety_sl_pips>0.0)
        {
         if(dir==NT_DIR_BUY) sl=bid-safety_sl_pips*pip;
         if(dir==NT_DIR_SELL) sl=ask+safety_sl_pips*pip;
        }

      if(!RetryBuySell(dir,each,comment,sl)) return(false);
      if(!RetryBuySell(dir,each,comment,sl)) return(false);

      if(use_pending && pending>0.0)
        {
         bool ok=false;
         for(int i=0;i<m_retry_count;i++)
           {
            if(dir==NT_DIR_BUY)
              {
               const double price=NormalizeDouble(ask-pending_offset_pips*pip,_Digits);
               ok=m_trade.BuyLimit(pending,price,m_symbol,(sl>0.0?sl:0.0),0.0,ORDER_TIME_GTC,0,comment);
              }
            else
              {
               const double price=NormalizeDouble(bid+pending_offset_pips*pip,_Digits);
               ok=m_trade.SellLimit(pending,price,m_symbol,(sl>0.0?sl:0.0),0.0,ORDER_TIME_GTC,0,comment);
              }
            if(ok) break;
            Sleep(120);
           }
         if(!ok) return(false);
        }
      return(true);
     }

   bool GetActiveBasket(NtBasketState &state)
     {
      ZeroMemory(state);
      state.active=false;
      datetime latest=0;
      double weighted_notional=0.0;

      for(int i=0;i<PositionsTotal();i++)
        {
         if(!PositionSelectByIndex(i)) continue;
         if(PositionGetString(POSITION_SYMBOL)!=m_symbol) continue;
         if((long)PositionGetInteger(POSITION_MAGIC)!=m_magic) continue;

         long basket_id=0;
         ENUM_NT_DIRECTION dir=NT_DIR_NONE;
         if(!NtParseBasketComment(PositionGetString(POSITION_COMMENT),basket_id,dir)) continue;

         const double vol=PositionGetDouble(POSITION_VOLUME);
         const double price=PositionGetDouble(POSITION_PRICE_OPEN);
         const datetime t=(datetime)PositionGetInteger(POSITION_TIME);
         state.active=true;
         state.basket_id=basket_id;
         state.direction=dir;
         if(state.first_open_time==0 || t<state.first_open_time) state.first_open_time=t;
         if(t>=latest) { latest=t; state.last_filled_price=price; }
         weighted_notional+=(price*vol);
         state.total_lots+=vol;
         state.floating_profit+=PositionGetDouble(POSITION_PROFIT);
         state.position_count++;
        }

      if(state.active && state.total_lots>0.0)
        {
         state.weighted_avg_price=weighted_notional/state.total_lots;
         state.dca_count=MathMax(0,state.position_count-2);
        }
      return(state.active);
     }

   bool CloseBasket(const long basket_id)
     {
      bool ok=true;
      for(int i=PositionsTotal()-1;i>=0;i--)
        {
         if(!PositionSelectByIndex(i)) continue;
         if(PositionGetString(POSITION_SYMBOL)!=m_symbol) continue;
         if((long)PositionGetInteger(POSITION_MAGIC)!=m_magic) continue;
         long id=0; ENUM_NT_DIRECTION d=NT_DIR_NONE;
         if(!NtParseBasketComment(PositionGetString(POSITION_COMMENT),id,d) || id!=basket_id) continue;
         const ulong pt=(ulong)PositionGetInteger(POSITION_TICKET);
         if(!m_trade.PositionClose(pt,m_deviation_points)) ok=false;
        }

      for(int j=OrdersTotal()-1;j>=0;j--)
        {
         const ulong ticket=OrderGetTicket(j);
         if(ticket==0 || !OrderSelect(ticket)) continue;
         if(OrderGetString(ORDER_SYMBOL)!=m_symbol) continue;
         if((long)OrderGetInteger(ORDER_MAGIC)!=m_magic) continue;
         long id=0; ENUM_NT_DIRECTION d=NT_DIR_NONE;
         if(!NtParseBasketComment(OrderGetString(ORDER_COMMENT),id,d) || id!=basket_id) continue;
         if(!m_trade.OrderDelete(ticket)) ok=false;
        }
      return(ok);
     }

   bool AddDca(const long basket_id,const ENUM_NT_DIRECTION dir,const double lots,const double safety_sl_pips)
     {
      const string comment=NtBuildBasketComment(basket_id,dir);
      const double bid=SymbolInfoDouble(m_symbol,SYMBOL_BID);
      const double ask=SymbolInfoDouble(m_symbol,SYMBOL_ASK);
      const double pip=NtPipSize(m_symbol);
      double sl=0.0;
      if(safety_sl_pips>0.0)
        {
         if(dir==NT_DIR_BUY) sl=bid-safety_sl_pips*pip;
         else sl=ask+safety_sl_pips*pip;
        }
      return(RetryBuySell(dir,NtNormalizeVolume(m_symbol,lots),comment,sl));
     }
  };

#endif
