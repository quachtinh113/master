#ifndef __NOWTRADING_LOGGER_MQH__
#define __NOWTRADING_LOGGER_MQH__

#include <NowTrading/Types.mqh>

class NtLogger
  {
private:
   int m_log_level;
   string m_symbol;
   string m_file_name;

public:
   void Init(const int log_level,const string symbol)
     {
      m_log_level=log_level;
      m_symbol=symbol;
      FolderCreate("NowTrading");
      m_file_name=StringFormat("NowTrading/%s_basket_log.csv",symbol);
      const bool exists=FileIsExist(m_file_name);
      const int f=FileOpen(m_file_name,FILE_CSV|FILE_READ|FILE_WRITE|FILE_SHARE_WRITE,',');
      if(f!=INVALID_HANDLE)
        {
         if(!exists)
            FileWrite(f,"timestamp","symbol","basket_id","event_type","direction","lots","price","rsi_h4","rsi_h1","rsi_m15","adx_h1","atr_m15","spread","equity","free_margin","dd_daily","dd_floating","note");
         FileClose(f);
        }
     }

   void Log(const int level,const string event_type,const long basket_id,const ENUM_NT_DIRECTION dir,
            const double lots,const double price,const NtSignalSnapshot &sig,const NtRiskSnapshot &risk,
            const string note)
     {
      if(level>m_log_level)
         return;

      PrintFormat("[NowTrading][%s] basket=%I64d dir=%s lots=%.2f price=%.5f rsiH4=%.2f rsiH1=%.2f rsiM15(2/1)=%.2f/%.2f adx=%.2f atr=%.5f spread=%.1f dd(d/f)=%.2f/%.2f note=%s",
                  event_type,basket_id,NtDirectionToString(dir),lots,price,sig.rsi_h4,sig.rsi_h1,sig.rsi_m15_prev2,sig.rsi_m15_prev1,sig.adx_h1,sig.atr_m15,sig.spread_points,risk.dd_daily_percent,risk.dd_floating_percent,note);

      const int f=FileOpen(m_file_name,FILE_CSV|FILE_READ|FILE_WRITE|FILE_SHARE_WRITE,',');
      if(f==INVALID_HANDLE)
         return;
      FileSeek(f,0,SEEK_END);
      const string ts=TimeToString(TimeLocal(),TIME_DATE|TIME_SECONDS);
      FileWrite(f,ts,m_symbol,(string)basket_id,event_type,NtDirectionToString(dir),DoubleToString(lots,2),DoubleToString(price,_Digits),
                DoubleToString(sig.rsi_h4,2),DoubleToString(sig.rsi_h1,2),DoubleToString(sig.rsi_m15_prev1,2),DoubleToString(sig.adx_h1,2),
                DoubleToString(sig.atr_m15,_Digits),DoubleToString(sig.spread_points,1),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2),
                DoubleToString(AccountInfoDouble(ACCOUNT_FREEMARGIN),2),DoubleToString(risk.dd_daily_percent,2),DoubleToString(risk.dd_floating_percent,2),note);
      FileClose(f);
     }
  };

#endif
