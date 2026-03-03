#property strict
#property version   "1.00"
#property description "NowTrading 30M Basket EA"

#include <NowTrading/Types.mqh>
#include <NowTrading/Utils.mqh>
#include <NowTrading/Logger.mqh>
#include <NowTrading/TimeEngine.mqh>
#include <NowTrading/Indicators.mqh>
#include <NowTrading/SignalGate.mqh>
#include <NowTrading/RiskGuard.mqh>
#include <NowTrading/BasketManager.mqh>
#include <NowTrading/DcaEngine.mqh>

input long   InpMagic=3001001;
input double BaseLotsTotal=0.20;
input bool   UsePendingLimit=true;
input double PendingLots=0.10;
input double PendingOffsetPips=10.0;
input double DcaLots=0.20;
input double SpacingPips=30.0;
input int    MaxDcaLevels=3;
input int    TpMode=0; // 0=MONEY, 1=ATR
input double TargetProfitUSD=20.0;
input double AtrMultiplierTP=1.5;
input int    EmergencyHours=12;
input int    MaxSpreadPoints=25;
input int    DeviationPoints=20;
input double SafetySLPips=0.0;

input bool EnableLondonNYOnly=true;
input int  StartHour=7;
input int  EndHour=23;
input int  DailyMaxBaskets=3;

input double MaxDailyDdPercent=8.0;
input double MaxFloatingDdPercent=10.0;
input double MinFreeMarginPercent=50.0;
input int MaxConsecutiveLosingBaskets=3;
input bool EnableNewsBlackout=false;
input datetime ManualHighImpactNewsTime=0;
input int NewsWindowMinutes=15;
input bool EnableCorrelationGuard=false;

input int LogLevel=1;

NtLogger g_logger;
NtTimeEngine g_time;
NtIndicators g_ind;
NtSignalGate g_signal;
NtRiskGuard g_risk;
NtBasketManager g_basket;
NtDcaEngine g_dca;

int g_consecutive_losses=0;

double BasketTargetPrice(const NtBasketState &basket,const NtSignalSnapshot &sig)
  {
   const double dist=AtrMultiplierTP*sig.atr_m15;
   if(basket.direction==NT_DIR_BUY)
      return(basket.weighted_avg_price+dist);
   return(basket.weighted_avg_price-dist);
  }

bool IsBasketTpHit(const NtBasketState &basket,const NtSignalSnapshot &sig)
  {
   if((ENUM_NT_TP_MODE)TpMode==NT_TP_MONEY)
      return(basket.floating_profit>=TargetProfitUSD);

   const double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   const double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   const double tp_price=BasketTargetPrice(basket,sig);
   if(basket.direction==NT_DIR_BUY)
      return(bid>=tp_price);
   return(ask<=tp_price);
  }

bool EmergencyExitTriggered(const NtBasketState &basket,const NtSignalSnapshot &sig)
  {
   if(!basket.active)
      return(false);
   if((TimeLocal()-basket.first_open_time)<EmergencyHours*3600)
      return(false);

   if(basket.direction==NT_DIR_BUY)
      return(sig.rsi_h4<45.0 && sig.rsi_d1<50.0);
   if(basket.direction==NT_DIR_SELL)
      return(sig.rsi_h4>55.0 && sig.rsi_d1>50.0);
   return(false);
  }

void EvaluateBasketLifecycle(const NtSignalSnapshot &sig,const NtRiskSnapshot &risk)
  {
   NtBasketState basket;
   if(!g_basket.GetActiveBasket(basket))
      return;

   if(IsBasketTpHit(basket,sig))
     {
      const bool ok=g_basket.CloseBasket(basket.basket_id);
      g_logger.Log(NT_LOG_INFO,"BASKET_TP",basket.basket_id,basket.direction,basket.total_lots,basket.weighted_avg_price,sig,risk,(ok?"tp_close_ok":"tp_close_fail"));
      g_consecutive_losses=(basket.floating_profit<0.0?g_consecutive_losses+1:0);
      return;
     }

   if(EmergencyExitTriggered(basket,sig))
     {
      const bool ok=g_basket.CloseBasket(basket.basket_id);
      g_logger.Log(NT_LOG_INFO,"EMERGENCY_EXIT",basket.basket_id,basket.direction,basket.total_lots,basket.weighted_avg_price,sig,risk,(ok?"12h_rsi_exit_ok":"12h_rsi_exit_fail"));
      g_consecutive_losses=(basket.floating_profit<0.0?g_consecutive_losses+1:0);
      return;
     }

   if(basket.dca_count<MaxDcaLevels && !risk.block_dca && !risk.block_new_entries && g_dca.ShouldAdd(basket,SpacingPips))
     {
      const bool dca_ok=g_basket.AddDca(basket.basket_id,basket.direction,DcaLots,SafetySLPips);
      g_logger.Log(NT_LOG_INFO,"DCA_ADD",basket.basket_id,basket.direction,DcaLots,basket.last_filled_price,sig,risk,(dca_ok?"dca_ok":"dca_fail"));
     }
  }

void EvaluateNewEntry(const NtSignalSnapshot &sig,const NtRiskSnapshot &risk)
  {
   if(!g_time.IsEntryMinute())
      return;
   if(!g_time.IsSessionAllowed(EnableLondonNYOnly,StartHour,EndHour))
      return;
   if(!g_time.CanOpenInCurrentBlock(DailyMaxBaskets))
      return;
   if(risk.block_new_entries)
     {
      g_logger.Log(NT_LOG_INFO,"ENTRY_BLOCKED_RISK",0,NT_DIR_NONE,0.0,0.0,sig,risk,risk.reason);
      return;
     }

   NtBasketState current;
   if(g_basket.GetActiveBasket(current))
      return;

   const ENUM_NT_DIRECTION dir=g_signal.Evaluate(sig,MaxSpreadPoints);
   g_logger.Log(NT_LOG_DEBUG,"SIGNAL_EVAL",0,dir,0.0,0.0,sig,risk,"minute_01_31_gate");
   if(dir==NT_DIR_NONE)
      return;

   const long basket_id=g_basket.BuildBasketId();
   const bool ok=g_basket.OpenInitialBasket(basket_id,dir,BaseLotsTotal,UsePendingLimit,PendingLots,PendingOffsetPips,SafetySLPips);
   if(ok)
     {
      g_time.MarkBasketOpened();
      g_logger.Log(NT_LOG_INFO,"BASKET_OPEN",basket_id,dir,BaseLotsTotal,SymbolInfoDouble(_Symbol,SYMBOL_BID),sig,risk,"opened_2_market_plus_optional_limit");
     }
   else
      g_logger.Log(NT_LOG_ERROR,"BASKET_OPEN_FAIL",basket_id,dir,BaseLotsTotal,0.0,sig,risk,"execution_failed");
  }

int OnInit()
  {
   if(_Symbol!="EURUSD")
      Print("[NowTrading] Designed for EURUSD; continuing on current symbol by request scope.");

   g_time.Init();
   g_risk.Init();
   g_logger.Init(LogLevel,_Symbol);
   g_basket.Init(_Symbol,InpMagic,DeviationPoints,3);
   if(!g_ind.Init(_Symbol))
      return(INIT_FAILED);

   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   g_ind.Deinit();
  }

void OnTick()
  {
   g_time.OnTickRolloverCheck();
   g_risk.OnTickRolloverCheck();

   NtSignalSnapshot sig;
   if(!g_ind.Snapshot(sig))
      return;

   NtRiskSnapshot risk=g_risk.Evaluate(MaxDailyDdPercent,MaxFloatingDdPercent,MinFreeMarginPercent,
                                       g_consecutive_losses,MaxConsecutiveLosingBaskets,
                                       EnableNewsBlackout,NewsWindowMinutes,ManualHighImpactNewsTime,
                                       EnableCorrelationGuard);

   EvaluateBasketLifecycle(sig,risk);
   EvaluateNewEntry(sig,risk);
  }
