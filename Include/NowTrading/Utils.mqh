#ifndef __NOWTRADING_UTILS_MQH__
#define __NOWTRADING_UTILS_MQH__

double NtPipSize(const string symbol)
  {
   const int digits=(int)SymbolInfoInteger(symbol,SYMBOL_DIGITS);
   const double point=SymbolInfoDouble(symbol,SYMBOL_POINT);
   if(digits==3 || digits==5)
      return(point*10.0);
   return(point);
  }

double NtPipsToPrice(const string symbol,const double pips)
  {
   return(pips*NtPipSize(symbol));
  }

double NtNormalizeVolume(const string symbol,const double volume)
  {
   const double min_vol=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MIN);
   const double max_vol=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MAX);
   const double step=SymbolInfoDouble(symbol,SYMBOL_VOLUME_STEP);
   double v=MathMax(min_vol,MathMin(max_vol,volume));
   const double steps=MathRound(v/step);
   return(NormalizeDouble(steps*step,2));
  }

string NtDirectionToString(const ENUM_NT_DIRECTION dir)
  {
   if(dir==NT_DIR_BUY) return("BUY");
   if(dir==NT_DIR_SELL) return("SELL");
   return("NONE");
  }

string NtBuildBasketComment(const long basket_id,const ENUM_NT_DIRECTION dir)
  {
   return(StringFormat("NTB|%I64d|%s",basket_id,NtDirectionToString(dir)));
  }

bool NtParseBasketComment(const string comment,long &basket_id,ENUM_NT_DIRECTION &dir)
  {
   if(StringFind(comment,"NTB|")!=0)
      return(false);
   string parts[];
   const int n=StringSplit(comment,'|',parts);
   if(n<3)
      return(false);
   basket_id=(long)StringToInteger(parts[1]);
   dir=NT_DIR_NONE;
   if(parts[2]=="BUY") dir=NT_DIR_BUY;
   if(parts[2]=="SELL") dir=NT_DIR_SELL;
   return(dir!=NT_DIR_NONE);
  }

#endif
