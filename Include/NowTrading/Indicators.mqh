#ifndef __NOWTRADING_INDICATORS_MQH__
#define __NOWTRADING_INDICATORS_MQH__

#include <NowTrading/Types.mqh>

class NtIndicators
  {
private:
   string m_symbol;
   int m_rsi_h4;
   int m_rsi_h1;
   int m_rsi_m15;
   int m_rsi_d1;
   int m_adx_h1;
   int m_atr_m15;

   bool ReadSingle(const int handle,const int buffer,const int shift,double &value)
     {
      double arr[];
      if(CopyBuffer(handle,buffer,shift,1,arr)!=1)
         return(false);
      value=arr[0];
      return(true);
     }

public:
   bool Init(const string symbol)
     {
      m_symbol=symbol;
      m_rsi_h4=iRSI(symbol,PERIOD_H4,14,PRICE_CLOSE);
      m_rsi_h1=iRSI(symbol,PERIOD_H1,14,PRICE_CLOSE);
      m_rsi_m15=iRSI(symbol,PERIOD_M15,14,PRICE_CLOSE);
      m_rsi_d1=iRSI(symbol,PERIOD_D1,14,PRICE_CLOSE);
      m_adx_h1=iADX(symbol,PERIOD_H1,14);
      m_atr_m15=iATR(symbol,PERIOD_M15,14);
      return(m_rsi_h4!=INVALID_HANDLE && m_rsi_h1!=INVALID_HANDLE && m_rsi_m15!=INVALID_HANDLE && m_rsi_d1!=INVALID_HANDLE && m_adx_h1!=INVALID_HANDLE && m_atr_m15!=INVALID_HANDLE);
     }

   void Deinit()
     {
      if(m_rsi_h4!=INVALID_HANDLE) IndicatorRelease(m_rsi_h4);
      if(m_rsi_h1!=INVALID_HANDLE) IndicatorRelease(m_rsi_h1);
      if(m_rsi_m15!=INVALID_HANDLE) IndicatorRelease(m_rsi_m15);
      if(m_rsi_d1!=INVALID_HANDLE) IndicatorRelease(m_rsi_d1);
      if(m_adx_h1!=INVALID_HANDLE) IndicatorRelease(m_adx_h1);
      if(m_atr_m15!=INVALID_HANDLE) IndicatorRelease(m_atr_m15);
     }

   bool Snapshot(NtSignalSnapshot &out)
     {
      ZeroMemory(out);
      if(!ReadSingle(m_rsi_h4,0,1,out.rsi_h4)) return(false);
      if(!ReadSingle(m_rsi_h1,0,1,out.rsi_h1)) return(false);
      if(!ReadSingle(m_rsi_m15,0,2,out.rsi_m15_prev2)) return(false);
      if(!ReadSingle(m_rsi_m15,0,1,out.rsi_m15_prev1)) return(false);
      if(!ReadSingle(m_rsi_d1,0,1,out.rsi_d1)) return(false);
      if(!ReadSingle(m_adx_h1,0,1,out.adx_h1)) return(false);
      if(!ReadSingle(m_atr_m15,0,1,out.atr_m15)) return(false);
      const double ask=SymbolInfoDouble(m_symbol,SYMBOL_ASK);
      const double bid=SymbolInfoDouble(m_symbol,SYMBOL_BID);
      const double point=SymbolInfoDouble(m_symbol,SYMBOL_POINT);
      out.spread_points=(ask-bid)/point;
      return(true);
     }
  };

#endif
