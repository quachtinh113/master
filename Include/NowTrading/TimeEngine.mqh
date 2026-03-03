#ifndef __NOWTRADING_TIMEENGINE_MQH__
#define __NOWTRADING_TIMEENGINE_MQH__

class NtTimeEngine
  {
private:
   int m_last_entry_block_key;
   int m_daily_baskets;
   int m_last_day_of_year;

public:
   void Init()
     {
      m_last_entry_block_key=-1;
      m_daily_baskets=0;
      m_last_day_of_year=-1;
     }

   void OnTickRolloverCheck()
     {
      MqlDateTime lt;
      TimeToStruct(TimeLocal(),lt);
      if(m_last_day_of_year!=lt.day_of_year)
        {
         m_last_day_of_year=lt.day_of_year;
         m_daily_baskets=0;
         m_last_entry_block_key=-1;
        }
     }

   bool IsEntryMinute()
     {
      MqlDateTime lt;
      TimeToStruct(TimeLocal(),lt);
      return(lt.min==1 || lt.min==31);
     }

   bool IsSessionAllowed(const bool enabled,const int start_hour,const int end_hour)
     {
      if(!enabled)
         return(true);
      MqlDateTime lt;
      TimeToStruct(TimeLocal(),lt);
      if(start_hour<=end_hour)
         return(lt.hour>=start_hour && lt.hour<end_hour);
      return(lt.hour>=start_hour || lt.hour<end_hour);
     }

   int CurrentBlockKey()
     {
      MqlDateTime lt;
      TimeToStruct(TimeLocal(),lt);
      return(lt.year*100000 + lt.day_of_year*100 + (lt.hour*2 + (lt.min>=30 ? 1 : 0)));
     }

   bool CanOpenInCurrentBlock(const int daily_max_baskets)
     {
      if(m_daily_baskets>=daily_max_baskets)
         return(false);
      return(CurrentBlockKey()!=m_last_entry_block_key);
     }

   void MarkBasketOpened()
     {
      m_last_entry_block_key=CurrentBlockKey();
      m_daily_baskets++;
     }

   int DailyBaskets() const { return(m_daily_baskets); }
  };

#endif
