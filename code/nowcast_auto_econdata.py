# %%
import os
import numpy as np
import pandas as pd
from statsmodels.tsa.api import DynamicFactorMQ
from datetime import datetime
print("Loaded Packages Successfully")
# %%
def load_vintage(path):

    # Reading 
    series = pd.read_excel(path, sheet_name="series", engine='openpyxl')
    data = pd.read_excel(path, sheet_name="data_m", 
                        index_col="date", parse_dates=True, engine='openpyxl')
    data_logdiff = pd.read_excel(path, sheet_name="data_logdiff_m",
                                index_col="date", parse_dates=True, engine='openpyxl')
    gdp = pd.read_excel(path, sheet_name="data_q", 
                       index_col="date", parse_dates=True, engine='openpyxl')
    gdp_logdiff = pd.read_excel(path, sheet_name="data_logdiff_q", 
                        index_col="date", parse_dates=True, engine='openpyxl')
    
    # Subsetting 
    series_q = series.loc[series.freq == "Q"]
    series_m = series.loc[series.freq == "M"]
    data = data.loc[data.index >= "2000-01-01"]
    data_logdiff = data_logdiff.loc[data_logdiff.index >= "2000-01-01"]
    gdp = gdp.loc[gdp.index >= "2000-01-01"]
    gdp_logdiff = gdp_logdiff.loc[gdp_logdiff.index >= "2000-01-01"]

    # Period Index
    data.index = data.index.to_period()
    data_logdiff.index = data_logdiff.index.to_period()
    gdp.index = gdp.index.to_period()
    gdp_logdiff.index = gdp_logdiff.index.to_period()

    return dict(series = series, series_m = series_m, series_q = series_q,
                data = data, data_logdiff = data_logdiff, gdp = gdp, gdp_logdiff = gdp_logdiff)

# %%
vintages = os.listdir("vintages")
# %%
vintage_dates = {x: datetime.strptime(x[22:32], "%d_%m_%Y") for x in vintages}
vintage_quarters = {k: pd.Period(v, freq="Q") for k, v in vintage_dates.items()}
# %%
# Determine latest and previous vintages
latest_vintage = max(vintage_dates, key = vintage_dates.get)
# Determine previous vintage
def removekey(d, key):
    r = dict(d)
    del r[key]
    return r
previous_vintage = max(removekey(vintage_dates, latest_vintage), key = vintage_dates.get)
# %% 
# Determine first vintage for this quarter: used for standardization
today = datetime.date(max(vintage_dates.values())) # datetime.today()
today_q = vintage_quarters[latest_vintage]
today_m = today_q.to_timestamp(freq = "M", how = "end").to_period(freq = "M") # Safer (more precise)
vintages_this_quarter = {k: v for k, v in vintage_quarters.items() if v == today_q}
first_vintage = min(vintages_this_quarter, key = vintage_dates.get)
# %% 
# Print some info
print(f"\nToday is {str(today)}. We are nowcasting for Quarter {today_q}. This is month {today_m}.\n" +
      f"The latest vintage is {latest_vintage} from {vintage_dates[latest_vintage]}.\n" +
      f"The previous vintage is {previous_vintage} from {vintage_dates[previous_vintage]}.\n" +
      f"The first vintage for this quarter is {first_vintage} from {vintage_dates[first_vintage]}.\n" +
      f"There are {len(vintages_this_quarter)} vintages for this quarter so far.\n")
# %%
# Load data as necessary. Note that we need to get the first vintage for this quarter in order for all news
# computations to be comparable within the quarter. This is because data is standardized, and we use the first
# vintage to obtain the means and scale factors for each series to apply to all other vintages in the quarter.
first_data = load_vintage("vintages/" + first_vintage)
previous_data = load_vintage("vintages/" + previous_vintage) if previous_vintage != first_vintage else first_data
latest_data = load_vintage("vintages/" + latest_vintage) if latest_vintage != first_vintage else first_data
print("loaded vintages successfully")
# %%
# Print series count by broad sector (first vintage this quarter)
print(first_data["series"].groupby('broad_sector', sort=False)["series"].count())
# %%
# Saving series csv (first vintage this quarter): updates to the model only possibly in the next quarter
first_data["series"][["series", "series_orig", "dataset", "label", "freq", "unit", "seas_adj", "broad_sector", "topic"]] \
    .to_csv("nowcast/series.csv", index=False)
# %% 
# Saving latest gdp
latest_data["gdp"].to_csv("nowcast/gdp.csv", index_label="quarter")
latest_data["gdp_logdiff"].to_csv("nowcast/gdp_logdiff.csv", index_label="quarter")
# %%
# Factors labels and factor specification
series = first_data["series"]
labels = {k: v for k, v in zip(series.series, series.label)}
factors = {l: ['Global', v] for l, v in zip(series.series, series.broad_sector)}
# %%
# Fit DFM on the first vintage of the quarter: needed for standardization
dfm_first = DynamicFactorMQ(endog=first_data["data_logdiff"], 
                            endog_quarterly=first_data["gdp_logdiff"][["UNEMP", "GDP", "RGDP"]], 
                            factors=factors, 
                            factor_multiplicities=dict(Global = 2, Real = 2, Financial = 1, Fiscal = 2, External = 2), 
                            factor_orders=2)
dfm_first_results = dfm_first.fit(disp=10)
print("fitted dfm successfully")
# %% 
# Show a summary of the fit on the first vintage
# dfm_first_results.summary()
# %% 
# Now fitting the DFM on the previous and latest vintage, if different from the first vintage
dfm_previous_results = dfm_first_results.apply(endog = previous_data["data_logdiff"], 
                                               endog_quarterly=previous_data["gdp_logdiff"][["UNEMP", "GDP", "RGDP"]], 
                                               refit = True, retain_standardization = True) if previous_vintage != first_vintage else dfm_first_results

dfm_latest_results = dfm_first_results.apply(endog = latest_data["data_logdiff"], 
                                             endog_quarterly=latest_data["gdp_logdiff"][["UNEMP", "GDP", "RGDP"]], 
                                             refit = True, retain_standardization = True) if latest_vintage != first_vintage else dfm_first_results
print("applied dfm to other vintages successfully")
# %% 
# Show a summary of the fit on the latest vintage
# dfm_latest_results.summary()
# %% 
# First Nowcast
gdp_now_first = dfm_first_results.get_prediction(start = today_m) # today_q
print("First Nowcast")
print(gdp_now_first.predicted_mean[["UNEMP", "GDP", "RGDP"]])
# Previous Nowcast
gdp_now_prev = dfm_previous_results.get_prediction(start = today_m) # today_q
print("Previous Nowcast")
print(gdp_now_prev.predicted_mean[["UNEMP", "GDP", "RGDP"]])
# Current Nowcast
gdp_now = dfm_latest_results.get_prediction(start = today_m) # today_q
print("Current Nowcast")
print(gdp_now.predicted_mean[["UNEMP", "GDP", "RGDP"]])

# %%
# Generating a new row for the nowcast csv
# gdp_now.summary_frame(endog=-1)
nowcast = gdp_now.predicted_mean[["UNEMP", "GDP", "RGDP"]] # .resample("Q").last()
nowcast["date"] = today # - timedelta(days=7)
nowcast["quarter"] = str(today_q)
nowcast = nowcast[["date", "quarter", "UNEMP", "GDP", "RGDP"]]
print(nowcast)
# %% 
# Appending the row to the nowcast csv
nowcast_old = pd.read_csv("nowcast/nowcast.csv")
nowcast_all = pd.concat([nowcast_old.loc[pd.to_datetime(nowcast_old.date) < pd.to_datetime(today)], 
                         nowcast]).reset_index(drop = True)
nowcast_all.tail(3)
# %% 
# Saving the nowcast csv
nowcast_all.to_csv("nowcast/nowcast.csv", index = False)
# %%
# Now computing the news
news = dfm_latest_results.news(dfm_previous_results, 
                               impact_date = str(today_m), 
                               impacted_variable = ["UNEMP", "GDP", "RGDP"], 
                               comparison_type = "previous")
# %%
# Summarizing the news
print(news.summary(float_format='%.6f'))
# %%
# Generating data frame from the news
news_df = news.details_by_impact.reset_index() 
news_df["impact date"] = pd.PeriodIndex(news_df["impact date"]).to_timestamp(freq="Q")
news_df["quarter"] = str(today_q)
news_df["date"] = today # - timedelta(days=7)
news_df.head()
# %%
# Loading old news and appending the new news
news_old = pd.read_csv("nowcast/news.csv")
news_all = pd.concat([news_old.loc[pd.to_datetime(news_old.date) < pd.to_datetime(today)], 
                      news_df[news_old.columns]])
print(news_all.tail())
# %%
# Saving the updated news csv
news_all.to_csv("nowcast/news.csv", index = False)

# %%
