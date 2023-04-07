# Import packages
from dash import Dash, html, dash_table, dcc
# import plotly.express as px
import plotly.graph_objects as go

# %% 
import pandas as pd
nowcast = pd.read_csv("https://raw.githubusercontent.com/Stellenbosch-Econometrics/SA-Nowcast/main/nowcast/nowcast.csv") # index_col="date", parse_dates=True)
gdp_ld = pd.read_csv("https://raw.githubusercontent.com/Stellenbosch-Econometrics/SA-Nowcast/main/nowcast/gdp_logdiff.csv") # , index_col="quarter", parse_dates=True
gdp_ld.index = pd.PeriodIndex(gdp_ld.quarter, freq="Q")
gdp_ld = gdp_ld.loc[gdp_ld.index >= pd.PeriodIndex(nowcast.quarter, freq="Q").min()]
news = pd.read_csv("https://raw.githubusercontent.com/Stellenbosch-Econometrics/SA-Nowcast/main/nowcast/news.csv")
series = pd.read_csv("https://raw.githubusercontent.com/Stellenbosch-Econometrics/SA-Nowcast/main/nowcast/series.csv")
news = news.merge(series, 
                  left_on = "updated variable", 
                  right_on = "series", how = "left")

# %%
nowcast_final = nowcast.copy()
nowcast_final.date = pd.to_datetime(nowcast_final.date)
final_ids = nowcast_final.groupby('quarter').date.idxmax()
nowcast_final = nowcast.iloc[final_ids] # nowcast.groupby("quarter").last().reset_index()
nowcast_other = nowcast.drop(index = final_ids)
fig = go.Figure()
fig.add_trace(go.Scatter(x=nowcast_final.quarter, y=nowcast_final.RGDP, 
                         customdata=nowcast_final.date, 
                         hovertemplate="%{y:.2f} (%{customdata})",
                         mode='lines+markers', name='Latest Nowcast'))
fig.add_trace(go.Scatter(x=nowcast_other.quarter, y=nowcast_other.RGDP, 
                         customdata=nowcast_other.date, 
                         hovertemplate="%{y:.2f} (%{customdata})",
                         mode='markers', name='Nowcast'))
# choose last day of quarter as timestamp
fig.add_trace(go.Scatter(x=gdp_ld.quarter, y=gdp_ld.RGDP, hovertemplate="%{y:.2f}",
                         mode='lines+markers', name='Real GDP Growth')) # gdp_ld.index.to_timestamp(how = "end")
# Edit the layout
fig.update_layout(title='Nowcasts of Real GDP Growth',
                  xaxis_title='Quarter',
                  yaxis_title='Log-Differnece Growth Rate (%)')
# change the hovermode to compare data points
fig.update_layout(hovermode="x")
# make tight layout
fig.update_layout(autosize=False, width=750, height=500, 
                  margin=dict(l=20, r=20, t=40, b=20))


# News digest
news_tot = news.loc[news["impacted variable"] == "RGDP"] \
    .groupby(["broad_sector", "topic"]) \
    .agg({"weight": "mean", "impact": "mean"}).reset_index() 
news_tot["sector_topic"] = news_tot.broad_sector + ": " + news_tot.topic
news_tot["abs_impact"] = news_tot.impact.abs() * 100
news_tot.head()

# %%
tot_news_fig = go.Figure()
tot_news_fig.add_bar(x=news_tot.sector_topic, y=news_tot.abs_impact)
tot_news_fig.update_layout(title='Average Absolute News Impact on Real GDP',      
                    xaxis_title='Date', yaxis_title='Average Absolute Impact',
                    barmode='stack',
                    hovermode="x", 
                    autosize=False, width=750, height=500,
                    margin=dict(l=20, r=20, t=40, b=20))

# 
app = Dash(__name__)


app.layout = html.Div([
    # html.Div(children='My First App with Data'),
    html.H1("South Afirca Nowcast"),
    dash_table.DataTable(data=nowcast.to_dict('records'), page_size=10),
    html.Hr(),
    html.Div(children='All Nowcasts'),
    dcc.Graph(figure = fig),
    dcc.Graph(figure = tot_news_fig)
    # px.line(x=nowcast.index, y=nowcast.RGDP, title="Nowcast of Real GDP", 
    #    labels = dict(x ="Quarter", y ="RGDP Logdiff")).update_traces(hovertemplate=None).update_layout(hovermode="x")
])

if __name__ == '__main__':
    app.run_server(debug=True)
# 

# %%
