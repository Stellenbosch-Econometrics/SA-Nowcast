#######################################
# Nowcasting Data EconData Clean
#######################################

options(repos = c(CRAN = "https://cloud.r-project.org"))
if(!requireNamespace("fastverse", quietly = TRUE)) install.packages("fastverse")
if(!requireNamespace("samadb", quietly = TRUE)) install.packages("https://www.dropbox.com/s/jpjitlb1njisdfq/samadb_0.2.2.9000.tar.gz?dl=1", repos = NULL, type = "source")
library(fastverse)
fastverse_extend(samadb, seastests, seasonal, tseries, tsbox, xts, writexl, install = TRUE)


# Seasonally Adjusting Relevant Indicators
seasadj <- function(x) {
  cc <- whichNA(x, invert = TRUE)
  if(length(cc) < 10) return(rep(NA_real_, length(x)))
  x[cc] <- tryCatch(final(seas(x)), error = function(e) tryCatch(final(seas(x, outlier = NULL)), 
                                                                 error = function(e2) forecast::seasadj(stl(na.omit(x), "periodic"))))
  x
}

# Imputing internal NA's for seasonal adjustment
spline_impute <- function(X) {
  for(i in seq_col(X)) {
    x <- X[, i]
    nnai <- whichNA(x, invert = TRUE)
    ln <- length(nnai)
    t1 <- nnai[1L]
    t2 <- nnai[ln]
    if (ln != t2 - t1 + 1L) 
      x[t1:t2] <- spline(nnai, x[nnai], xout = t1:t2)$y
    X[, i] = x
  }
  X
}

# Helper for log-differencing 
adjust_negative <- function(x) if(any((min <- fmin(x)) <= 0)) x %r+% iif(min <= 0, -min+1, 0) else x


#
### Final Selection of Series from EconData --------------------------------------------------------------------------------------------
#

econdata_monthly <- list(
  Real = list(
    Production = list( # Multiple R-squared:  0.3613
      KBP7085N = c("MAN001_I_S", "MAN001_S_S"),  # Total Manufacturing (Business cycles + Rand)
      KBP7062N = c("MIN001_I_S", "MIN001_S_S"),  # Total Mining Production, Seas. Adj.
      KBP7068N = c("ELE002_I_S", "ELE001_S_S")   # Electricity Generation and availability for distr. in SA # ELE003_S_N 
    ),
    Sales = list( # Multiple R-squared:  0.1832
      KBP7067N = c("MTS003_S", "MTS005_N"),      # Total motor trade and new vehicle sales (replaces Number of vehicles sold, Seas Adj. Index)
      KBP7086T = .c(RET008_I_S, RET008_S_S),     # Retail Sales 
      KBP7087T = .c(WHO001_I_S, WHO001_S_S)      # Wholesale Sales
    ),
    Prices = list( # Multiple R-squared:  0.1085
      KBP7155N = c("CPI60001", "CPI1000_M_N"),   # CPI Headline
      KBP7198M = c("PPI001", "PPI027", "PPI028", "PPI041") # Producer prices. Replaced with total, final manufactures, petrol and motor vehicles 
    ),
    Tourism = list( # Multiple R-squared:  0.8654
      MIGRATION = .c(MIG001_A_N0_TA, MIG001_A_A0_TA, MIG011_N_A0_TX, MIG011_N_N0_TX),  # Total + Total Air + Total overnight tourists + Air
      TOURIST_ACCOMMODATION = .c(TOU036_S, TOU006_S, TOU011_S)         # Total income, Stay Units Nights Sold and Occupancy rate
    ),
    `Other Real` = list( # Multiple R-squared:  0.4357
      KBP7090N = "DIFN003_M_S", # Leading Indicator
      LAND_TRANSPORT = .c(LAN001_S, LAN002_S, LAN018_S, LAN019_S) # Not really very current information...
    )
  ),
  Financial = list( # Multiple R-squared:  0.005111
    `Money and Credit` = list(
      FINANCIAL_SECTOR = "MON0088_M", # M0 
      KBP1374M = "MON0300_M",             # M3
      KBP1347M = "MON0023_M",             # PSC
      KBP1367M = "MON0191_M"              # Credit to the Government 
    ),
    `Other Fiancial` = list( # Multiple R-squared:  0.01558
      FINANCIAL_SECTOR = "MON0263_M", # NFA
      LIQUIDATIONS = "LIQ002_A_L_A_N" # Total Liquidations and Insolvencies (could ad more, any signal value??)
    )
  ),
  External = list(
    Trade = list( # Multiple R-squared:  0.2809
      EXTERNAL_SECTOR = .c(CURX600_M, CURM600_M) # Exports and Imports
    ),
    `Exchange Rates` = list( # Multiple R-squared:  0.003367
      KBP5339M = "BOP5329_M",   # Rand <-> USD Exchange Rate
      KBP5393M = "BOP5393_M"    # NEER
    ),
    Reserves = list( # Multiple R-squared:  0.02715
      KBP1021M = "BOP5806_M",     # Total reserves
      EXTERNAL_SECTOR = "BOP5272_M" # Foreign currency reserves
    )
  ),
  Fiscal = list(
    `Cash Flow` = list( # Multiple R-squared:  0.8279
        KBP4597M = "NGFC020_M",   # Total Revenue (Replaced with Cash Flow Revenue)
        KBP4601M = "NGFC040_M",   # Total Expenditure (Replaced with Cash Flow Expenditure)
        KBP4050M = "NGFC050_M"    # Cash Flow Balance 
    ),
    Financing = list( # Multiple R-squared:  0.01947     
        KBP4022M = "NGFC102_M",   # Financing: Domestic Government Bonds
        KBP4026M = "NGFC103_M",   # Financing: Foreign Bonds and Loans
        KBP4023M = "NGFC101_M",   # Financing: Treasury Bills and Short-Term Loans
        KBP4003M = "NGFC006_M",   # Financing: Change in Cash Balances
        KBP4030M = "NGFC100_M"    # Total financing of national government 
    ),
    Debt = list( # Multiple R-squared:  0.005562
        KBP4114M = "NGD1213_M",   # Total loan debt of national government: Total gross loan debt
        KBP4105M = "NGD1209_M",   # Total loan debt of national government: Total domestic debt (replaced with marketable debt)
        KBP4108M = "NGD7900_M",   # Total loan debt of national government: Total foreign debt
        FISCAL_SECTOR = "NGD4500_M"  # Domestic non-marketable debt
    )
  )
)

# Note: these series are renamed, so the that DFM models reading the excel file continue to work, even if we change the data source
econdata_quarterly <- list(Real = list(`Other Real`= list(BUSINESS_CYCLES = c(UNEMP = "LABT079_Q_S")), 
                                        Production = list(NATL_ACC = c(GDP = "KBP6006_N_S", RGDP = "KBP6006_R_S")))) # KBP6006_R_N,               

#
### Creating Nowcasting Dataset ----------------------------------------------------------------------------------------------
#

nc_ind <- c(econdata_monthly, econdata_quarterly) %>% 
  rapply(qDF, how = "list") %>%
  unlist2d(c("broad_sector", "topic", "QB"), "series_alt", DT = TRUE) %>% 
  ftransform(series = X, QB = NULL, X = NULL)

nc_series = fselect(sm_series(), -topic)[series %in% nc_ind$series][nc_ind, on = "series"]
settransform(nc_series,
   minimal = topic %in% c("Production", "Sales", "Prices", "Tourism", "Other Real", "Trade", "Cash Flow"),
   series_orig = series, 
   series = iif(nchar(series_alt) > 2L, series_alt, series),
   series_alt = NULL
)

names_alt <- nc_series %$% set_names(series, series_orig)[series_orig != series]

nc_data_m <- sm_data(series = unlist(econdata_monthly, use.names = FALSE))

nc_data_q <- sm_data(series = unlist(econdata_quarterly, use.names = FALSE)) %>% frename(names_alt, .nse = FALSE)

# Adjusting Monthly Indicators
nc_seas_m <- nc_data_m %>% num_vars() %>% sapply(isSeasonal, freq = 12) %>% which()
nc_data_sa_ts <- nc_data_m %>% get_vars(c("date", names(nc_seas_m))) %>% as.xts() %>% ts_ts() %>% spline_impute()

for(i in seq_col(nc_data_sa_ts)) {
  cat(colnames(nc_data_sa_ts)[i], "\n")
  nc_data_sa_ts[, i] <- seasadj(nc_data_sa_ts[, i])
}

get_vars(nc_data_m, colnames(nc_data_sa_ts)) <- mctl(nc_data_sa_ts)
nc_series[series %in% colnames(nc_data_sa_ts), seas_adj := TRUE]

# Transformed datasets
nc_rates_m <- nc_series[freq == "M" & unit %ilike% "Percentage", series]
nc_data_m_logdiff <- nc_data_m %>% 
  ftransform(fselect(., -date) %>% 
               adjust_negative() %>% 
               tfmv(nc_rates_m, function(x) x/100 + 1) %>% 
               fgrowth(logdiff = TRUE)) 

nc_rates_q <- nc_series[freq == "Q" & unit %ilike% "Percentage", series]
nc_data_q_logdiff <- nc_data_q %>% 
  ftransform(fselect(., -date) %>% 
               adjust_negative() %>% 
               tfmv(nc_rates_q, function(x) x/100 + 1) %>% 
               fgrowth(logdiff = TRUE)) 

# Percent of distinct values
print(sort(fndistinct(nc_data_m_logdiff)/fnobs(nc_data_m_logdiff)) * 100)
print(sort(fndistinct(nc_data_q_logdiff)/fnobs(nc_data_q_logdiff)) * 100)

# Correlations with quarterly indicators
nc_corrs <- nc_data_m_logdiff %>% merge(nc_data_q_logdiff, by = "date") %>% 
  fselect(-date) %>% pwcor(., gv(., names_alt)) %>% qDT("series") %>% 
  add_stub("corr_", cols = -1) %>% frename(tolower) %>% 
  fmutate(avg_abs_corr = pmean(abs(corr_unemp), abs(corr_gdp), abs(corr_rgdp)))

if(!all(nc_corrs$series %in% nc_series$series)) stop("missing series")
nc_series = nc_series[nc_corrs, on = "series"]

# Saving Data
list(series = nc_series, 
     data_m = nc_data_m, 
     data_q = nc_data_q, 
     data_logdiff_m = nc_data_m_logdiff, 
     data_logdiff_q = nc_data_q_logdiff) %>% 
  write_xlsx(sprintf("vintages/econdata_nowcast_data_%s.xlsx", format(Sys.Date(), "%d_%m_%Y")))


