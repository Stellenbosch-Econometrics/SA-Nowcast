library(fastverse)
fastverse_extend(xts, tsbox, seasonal, ggplot2, dfms, samadb, install = TRUE)

# This just gets the full database overview tables
DATASOURCE = sm_datasources() %T>% View()
DATASET = sm_datasets() %T>% View()
SERIES = sm_series() %T>% View()

# Get a small dataset on business cycles
BC = sm_data("BUSINESS_CYCLES")
# Show series codes and labels, and summarize
namlab(BC)
qsu(BC, vlabels = TRUE)
# Plot the monthly series after 2010
BC %>% gvr("date|_M_") %>% sbt(date >= sm_as_date(2010)) %>% as.xts() %>% plot(legend.loc = "topleft")

# Get daily data from the Quarterly Bulletin for financial year 2020/21
QB_D = sm_data("QB", freq = "D", from = "2020Q2", to = "2021Q1")
# Compute growth rates and summarize
QB_D %>% G(t = ~ date) %>% replace_Inf() %>% qsu()

# See what series we have on electricity
sm_series("ELECTRICITY")
# Query seasonally adjusted values and volumes of electricity production
sm_data(series = .c(ELE001_S_S, ELE002_I_S)) %>% as.xts() %>% STD() %>% plot(legend.loc = "topleft")

# We could merge this with BC, or simply let the database do it for us
BC_ELC = sm_data("BUSINESS_CYCLES", series = "ELE001_S_S", from = 2010)
BC_ELC %>% gvr("_Q_", invert = TRUE) %>% as.xts() %>% STD() %>% plot(legend.loc = "topleft")
# Some more API functions. Could also specify expand.date = TRUE and wide = FALSE in sm_data()
BC_ELC %>% gvr("CPI|PPI", invert = TRUE) %>% sm_expand_date() %>%   # Additional identifiers
  collap( ~ year + quarter, fmean, flast) %>%                       # Aggregate to quarterly frequency
  sm_pivot_longer() %>% fmutate(value = STD(value, series)) %>%     # Reshape and standardize
  ggplot(aes(x = date, y = value, colour = label)) + geom_line() +  # Plot
  guides(colour = guide_legend(ncol = 1)) + theme(legend.position = "bottom")
# Only in R: Transposition of data and saving to excel
BC_ELC %>% sm_transpose(date.format = "%m/%Y") %>% sm_write_excel("BC_ELC.xlsx")

# Now let's get a more interesting dataset
ind <- .c(
  KBP7091N, KBP7090N, # Coincident and leading business cycle indicators
  MAN001_S_S, MIN001_S_S, # Total manufacturing and mining production
  MTS003_S, RET008_S_S, WHO001_S_S, # Motortrade, wholesale and retail trade
  KBP7082T, KBP7195M, KBP7202M, KBP7203M, KBP7204M, # Manufacturing orders, sales and inventories
  KBP7196M, # Cargo at South African Ports
  CPI60001, PPI001, # Consumer and producer prices
  KBP1260M, KBP1261M, # Value and volume of credit card purchses
  KBP1368M, KBP1347M, # Total credit and credit to the private sector
  KBP1474M, KBP1478M, # New mortgages and mortgages paid out
  MIG001_A_N0_TA, MIG001_A_A0_TA, TOU036_S, TOU011_S, # Tourism
  CURX600_M, CURM600_M, # Exports and imports
  NGFC020_M, NGFC040_M, # Cash flow revenue and expenditure
  KBP5393M, KBP5395M, # Nominal and real effective exchange rates
  ELE001_S_S, ELE002_I_S # Electricity generation
)
# Get metdata of requested series: in this order (default is a fixed order)
series <- sm_series(series = ind)[match(ind, series)]
# Get data (default is to maintain the requested order if only series are requested)
data <- sm_data(series = ind, from = max(series$from_date))
# Basic exploration
qsu(data, vlabels = TRUE)
data %>% as.xts() %>% STD() %>% plot(lwd = 1)
# Getting series not seasonally adjusted and adjusting them with X13
sadj_ind <- series %$% series[!seas_adj]
get_vars(data, sadj_ind) <- data %>% get_vars(c("date", sadj_ind)) %>%
  as.xts() %>% ts_ts() %>% seas() %>% final() %>% mctl()
# Computing growth rates
data_growth <- data %>% G(t = ~ as.yearmon(date), stub = FALSE) %>% replace_Inf()
data_growth %>% as.xts() %>% STD() %>% plot(lwd = 1)
# Compute and plot greatest correlations with electricity generation
oldpar <- par(mai = c(.5,6,.5,.5))
data_growth[year(date) != 2020] %>% num_vars() %>% pwcor() %>%
  ss(rownames(.) %!in% .c(ELE001_S_S, ELE002_I_S), .c(ELE001_S_S, ELE002_I_S)) %>%
  rowMeans() %>% sort() %>% barplot(horiz = TRUE, las = 1, main = "Average Correlation with Electricity Generation (in Growth Rates)",
    names.arg = paste0(names(.), ": ", series[match(names(.), series), label] %>% substr(1, 55)))
par(oldpar)
# Estimate a dynamic factor coincident index
dfm_mod <- DFM(num_vars(data_growth), 1, 3, idio.ar1 = TRUE)
plot(dfm_mod, method = "all")



