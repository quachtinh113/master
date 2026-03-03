#ifndef __NOWTRADING_DCAENGINE_MQH__
#define __NOWTRADING_DCAENGINE_MQH__

#include <NowTrading/Types.mqh>
#include <NowTrading/Utils.mqh>

class NtDcaEngine
  {
public:
   bool ShouldAdd(const NtBasketState &basket,const double spacing_pips)
     {
      if(!basket.active || basket.direction==NT_DIR_NONE)
         return(false);
      const double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
      const double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
      const double spacing=NtPipsToPrice(_Symbol,spacing_pips);
      if(basket.direction==NT_DIR_BUY)
         return((basket.last_filled_price-bid)>=spacing);
      return((ask-basket.last_filled_price)>=spacing);
     }
  };

#endif
