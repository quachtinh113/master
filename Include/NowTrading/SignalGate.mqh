#ifndef __NOWTRADING_SIGNALGATE_MQH__
#define __NOWTRADING_SIGNALGATE_MQH__

#include <NowTrading/Types.mqh>

class NtSignalGate
  {
public:
   ENUM_NT_DIRECTION Evaluate(const NtSignalSnapshot &sig,const double max_spread_points)
     {
      const bool spread_ok=(sig.spread_points<=max_spread_points);
      const bool cross_above=(sig.rsi_m15_prev2<=50.0 && sig.rsi_m15_prev1>50.0);
      const bool cross_below=(sig.rsi_m15_prev2>=50.0 && sig.rsi_m15_prev1<50.0);

      const bool buy=(sig.rsi_h4>55.0 && sig.rsi_h1>50.0 && cross_above && sig.adx_h1>22.0 && spread_ok);
      const bool sell=(sig.rsi_h4<45.0 && sig.rsi_h1<50.0 && cross_below && sig.adx_h1>22.0 && spread_ok);

      if(buy) return(NT_DIR_BUY);
      if(sell) return(NT_DIR_SELL);
      return(NT_DIR_NONE);
     }
  };

#endif
