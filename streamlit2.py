# -*- coding: utf-8 -*-
"""
Created on Wed Mar 24 17:19:02 2021

@author: Ben.Simpson
"""
#%% # Prelims

import pandas as pd
import requests
import json
import numpy as np
import streamlit as st
import plotly.express as px


st.set_page_config(
   page_title="BS FPL",
   page_icon=":soccer:",
   layout="wide",
   initial_sidebar_state="collapsed",
 )

config = {'displayModeBar': False}




#%% Functions


## Get the JSON from an URL
@st.cache_data()
def BSget(url):
    response = requests.get(url)
    return json.loads(response.content)


## Get this years gameweek data by playerID
@st.cache_data()
def BSget_entry_season(entryid):
    entry = BSget("https://fantasy.premierleague.com/api/entry/%s/" % entryid)
    
    ManagerName = entry['player_first_name'] + ' ' + entry['player_last_name']
    ManagerTeamName = entry['name']
    
    entryseason = BSget("https://fantasy.premierleague.com/api/entry/%s/history/" % entryid)
    entryseason_df = pd.DataFrame(entryseason['current'])
    entryseason_df['ManagerName'] = ManagerName
    entryseason_df['ManagerTeamName'] = ManagerTeamName  
    
    chips = pd.DataFrame(entryseason['chips']).drop(columns = 'time', errors='ignore').rename(columns = {'name' : 'Chip'})

    try:
        entryseason_df = pd.merge(
            entryseason_df,
            chips,
            how = 'left',
            on = 'event'
            )
    except KeyError:
        entryseason_df['Chip'] = np.nan
        
    for i in ['event_transfers', 'event_transfers_cost','points_on_bench']:
        entryseason_df[i + '_cum'] = entryseason_df.sort_values(['ManagerName', 'ManagerTeamName', 'event']).groupby(['ManagerName', 'ManagerTeamName'])[i].cumsum()

    return(entryseason_df)

## Run BSget_entry_season through all members of a classic league
@st.cache_data()
def BSget_entry_season_league(leagueid):
    league_d = BSget('https://fantasy.premierleague.com/api/leagues-classic/%s/standings' % leagueid)
    league_entries = pd.DataFrame(league_d['standings']['results'])['entry'].unique()
    
    league_season = pd.DataFrame()
    
    for entryid in league_entries:
        league_season = pd.concat([league_season, BSget_entry_season(entryid)])
        
    league_season['LeagueName'] = league_d['league']['name']
    
    league_season['PlayerRanking'] = league_season.groupby('event')['overall_rank'].rank()
        
    return(league_season)
#%% Start

st.title("BS Fantasy Football")
my_expander = st.expander("Data Load", expanded=True)
with my_expander:
    league_id = st.text_input('Enter League ID', '605567')
    data_load_state = st.text('Loading data...')
    data_season = BSget_entry_season_league(league_id)
    data_load_state.text('Loading data...done! Check out the %s league' % data_season['LeagueName'].unique()[0])


#%% Sidebar
managers = data_season.ManagerName.unique().tolist()

container = st.container()
all = st.sidebar.checkbox("Select all", True)
 
if all:
    player_select = st.sidebar.multiselect('Select Managers:', managers, managers)
else:
    player_select = st.sidebar.multiselect('Select Managers:', managers)



data_season_mask = data_season['ManagerName'].isin(player_select)

data_season = data_season[data_season_mask]

#%% Current Status

st.header('Current Status')

CurrentTab = data_season[data_season.event == data_season.event.max()].set_index(['ManagerName', 'ManagerTeamName']).drop(columns=['points',  'rank', 'rank_sort', 'event_transfers', 'event_transfers_cost', 'points_on_bench', 'Chip', 'LeagueName'])
st.dataframe(CurrentTab)

#%% Overall Rank
st.header('Overall Rank')
fig_OR = px.line(data_season, x="event", y='overall_rank', color='ManagerName', hover_data = ['points', 'total_points'], height=800, line_shape='spline').update_yaxes(autorange="reversed")

st.plotly_chart(fig_OR,  use_container_width=True, config=config)

#%% Player Rank
st.header('Player Rank')
fig_Rk = px.line(data_season, x="event", y='PlayerRanking', color='ManagerName', height=800, line_shape='spline').update_yaxes(autorange="reversed")

st.plotly_chart(fig_Rk,  use_container_width=True, config=config)
#%% Point on the Bench
st.header('Point on the Bench')

fig_PB = px.line(data_season, x="event", y='points_on_bench_cum', color='ManagerName', height=800, line_shape='spline')

st.plotly_chart(fig_PB,  use_container_width=True, config=config)

#%% Team Value
st.header('Team Value')
fig_TV = px.line(data_season, x="event", y='value', color='ManagerName', height=800, line_shape='spline')

st.plotly_chart(fig_TV,  use_container_width=True, config=config)

#%% Transfers
st.header('Transfers')
transfer_df = pd.melt(data_season, id_vars = ['ManagerName', 'ManagerTeamName', 'event'], value_vars=['event_transfers_cum', 'event_transfers_cost_cum'], var_name = 'metric', value_name='count')
fig_TR = px.line(transfer_df, x="event", y='count', color='ManagerName', facet_row = 'metric', height=800, line_shape='spline')
fig_TR.layout.yaxis2.update(matches=None)
st.plotly_chart(fig_TR,  use_container_width=True, config=config)

#%% Rival Watch

st.header('Rival Watch')


left_column, right_column = st.beta_columns(2)
player1 = left_column.selectbox('Manager 1:', managers, 0)
player2 = right_column.selectbox('Manager 2:', managers, 1)


data_rivals = data_season[data_season['ManagerName'].isin([player1,player2])]

data_rivals = data_rivals.pivot(index = ['event'], columns = 'ManagerName', values = 'total_points').assign(Diff = lambda x: x[player1]-x[player2]).reset_index()

fig_RV = px.line(data_rivals, x="event", y='Diff', height=800, line_shape='spline')
st.plotly_chart(fig_RV,  use_container_width=True, config=config)
