#ifndef __NOWTRADING_TYPES_MQH__
#define __NOWTRADING_TYPES_MQH__

enum ENUM_NT_DIRECTION
  {
   NT_DIR_NONE = 0,
   NT_DIR_BUY  = 1,
   NT_DIR_SELL = -1
  };

enum ENUM_NT_TP_MODE
  {
   NT_TP_MONEY = 0,
   NT_TP_ATR   = 1
  };

enum ENUM_NT_LOG_LEVEL
  {
   NT_LOG_ERROR = 0,
   NT_LOG_INFO  = 1,
   NT_LOG_DEBUG = 2
  };

struct NtSignalSnapshot
  {
   double rsi_h4;
   double rsi_h1;
   double rsi_m15_prev2;
   double rsi_m15_prev1;
   double rsi_d1;
   double adx_h1;
   double atr_m15;
   double spread_points;
  };

struct NtRiskSnapshot
  {
   bool block_new_entries;
   bool block_dca;
   double dd_daily_percent;
   double dd_floating_percent;
   double free_margin_percent;
   int consecutive_losing_baskets;
   string reason;
  };

struct NtBasketState
  {
   bool active;
   long basket_id;
   ENUM_NT_DIRECTION direction;
   datetime first_open_time;
   double weighted_avg_price;
   double floating_profit;
   int position_count;
   int dca_count;
   double total_lots;
   double last_filled_price;
  };

#endif
