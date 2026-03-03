#ifndef __NOWTRADING_RISKGUARD_MQH__
#define __NOWTRADING_RISKGUARD_MQH__

#include <NowTrading/Types.mqh>

class NtRiskGuard
  {
private:
   double m_day_start_equity;
   int m_day_of_year;

public:
   void Init()
     {
      MqlDateTime lt;
      TimeToStruct(TimeLocal(),lt);
      m_day_of_year=lt.day_of_year;
      m_day_start_equity=AccountInfoDouble(ACCOUNT_EQUITY);
     }

   void OnTickRolloverCheck()
     {
      MqlDateTime lt;
      TimeToStruct(TimeLocal(),lt);
      if(lt.day_of_year!=m_day_of_year)
        {
         m_day_of_year=lt.day_of_year;
         m_day_start_equity=AccountInfoDouble(ACCOUNT_EQUITY);
        }
     }

   bool IsNewsBlackout(const bool enabled,const int minutes_before_after,const datetime manual_news_time)
     {
      if(!enabled || manual_news_time<=0)
         return(false);
      const int delta=(int)MathAbs((double)(TimeLocal()-manual_news_time));
      return(delta<=minutes_before_after*60);
     }

   bool CorrelationGuardBlocks(const bool enabled)
     {
      if(!enabled)
         return(false);
      return(false);
     }

   NtRiskSnapshot Evaluate(const double max_daily_dd,const double max_float_dd,const double min_free_margin_pct,
                           const int consecutive_losses,const int max_consecutive_losses,
                           const bool news_enabled,const int news_window_minutes,const datetime manual_news_time,
                           const bool correlation_enabled)
     {
      NtRiskSnapshot s;
      ZeroMemory(s);
      s.reason="";
      s.consecutive_losing_baskets=consecutive_losses;

      const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
      const double balance=AccountInfoDouble(ACCOUNT_BALANCE);
      const double margin=AccountInfoDouble(ACCOUNT_MARGIN);
      const double free_margin=AccountInfoDouble(ACCOUNT_FREEMARGIN);

      s.dd_daily_percent=(m_day_start_equity>0.0 ? MathMax(0.0,(m_day_start_equity-equity)/m_day_start_equity*100.0) : 0.0);
      s.dd_floating_percent=(balance>0.0 ? MathMax(0.0,(balance-equity)/balance*100.0) : 0.0);
      s.free_margin_percent=((margin+free_margin)>0.0 ? free_margin/(margin+free_margin)*100.0 : 100.0);

      s.block_new_entries=false;
      s.block_dca=false;

      if(s.dd_daily_percent>max_daily_dd) { s.block_new_entries=true; s.reason+="daily_dd;"; }
      if(s.dd_floating_percent>max_float_dd) { s.block_new_entries=true; s.reason+="float_dd;"; }
      if(consecutive_losses>=max_consecutive_losses) { s.block_new_entries=true; s.reason+="consecutive_losses;"; }
      if(IsNewsBlackout(news_enabled,news_window_minutes,manual_news_time)) { s.block_new_entries=true; s.reason+="news_blackout;"; }
      if(CorrelationGuardBlocks(correlation_enabled)) { s.block_new_entries=true; s.reason+="correlation;"; }

      if(s.dd_floating_percent>6.0) { s.block_dca=true; s.reason+="dca_float_dd;"; }
      if(s.free_margin_percent<min_free_margin_pct) { s.block_dca=true; s.reason+="dca_free_margin;"; }

      return(s);
     }
  };

#endif
