"""
Created on Wed Mar 31 14:53:56 2021

@author: Ben

Live Gameweek League Tracker

Points
Players Played
Players Blanked
Best Player
Transfers In/Out
Transfer Cost
Captain
Vice Captain
Points on the bench
Chip Used
Think about doubles and blanks


Event Stats
Deadline
Avg so far
Last game
Most C/VCed
top player (Include pictures?)
chips played (above average/below average arrow)

Next Deadline (countdown)


learn how to add icons (through HTML/CSS?)
"""
#%% Prelims

import pandas as pd
import requests
import json

import streamlit as st


st.set_page_config(
   page_title="BS FPL",
   page_icon=":soccer:",
   layout="wide",
   initial_sidebar_state="collapsed",
 )

config = {'displayModeBar': False}
#%% Functions
@st.cache(suppress_st_warning=True, allow_output_mutation=True)
def BSget(url):
    response = requests.get(url)
    return json.loads(response.content)


@st.cache(suppress_st_warning=True)
def BSgetStatic():
    response = BSget('https://fantasy.premierleague.com/api/bootstrap-static/')
    
    players_df = pd.DataFrame(response['elements'])
    events_df = pd.DataFrame(response['events'])
    
    events_df['deadline_time'] = pd.to_datetime(events_df['deadline_time'])
    events_df['deadline_time'] = events_df['deadline_time'].dt.tz_localize(None)

    events_df = pd.concat([events_df.drop(['top_element_info'], axis=1), events_df['top_element_info'].apply(pd.Series).rename(columns = {'id': 'TopPlayer', 'points': 'TopPlayerPoints'})], axis=1)

    events_df = pd.concat([
        events_df.drop(['chip_plays'], axis=1),
        pd.concat([
            events_df['chip_plays'].apply(pd.Series)[0].apply(pd.Series).drop(columns = 0), 
            events_df['chip_plays'].apply(pd.Series)[1].apply(pd.Series).drop(columns = 0),
            events_df['chip_plays'].apply(pd.Series)[2].apply(pd.Series).drop(columns = 0), 
            events_df['chip_plays'].apply(pd.Series)[3].apply(pd.Series).drop(columns = 0), 
            ]). \
            dropna(). \
            pivot(columns='chip_name', values='num_played')],
        axis=1)
    return([players_df, events_df])
 
@st.cache(suppress_st_warning=True)   
def GetPlayer1(col):
    return(players_mini[events_df.query('is_current')[col].item() == players_mini['id'].values])

 
@st.cache(suppress_st_warning=True)   
def GetPlayer1MD(Name, col):
    ms1 = GetPlayer1(col)
    
    mdtext = ("""
                ## %s
                ### %s 
                #### %s 
                """  % (Name, ms1.web_name.values[0], ms1.first_name.values[0]))
    mdimage = 'https://resources.premierleague.com/premierleague/photos/players/110x140/p%s.png' % ms1.code.values[0]
    return([mdtext, mdimage])


@st.cache(suppress_st_warning=True) 
def ChipMD(Name, col):
    tca = events_df.query('finished')[col].mean()
    tcc = events_df.query('is_current')[col].values[0]
    
    if tcc > tca:
        return("""
                       ## %s
                       %s :point_up_2:
                       """ % (Name, f'{tcc:,.0f}'))
    elif tcc < tca:
        return("""
                       ## %s
                       %s :point_down:
                       """ % (Name, f'{tcc:,.0f}'))
    else: 
        return("""
                   ## %s
                   %s
                   """ % (Name, f'{tcc:,.0f}'))
  
@st.cache(suppress_st_warning=True)                    
def get_entry_picks(manager_id, gw):
    entry_pick_t = BSget("https://fantasy.premierleague.com/api/entry/%s/event/%s/picks/" % (manager_id, gw))

    entry_pick_d = pd.DataFrame(entry_pick_t['picks'])
    entry_pick_d['Week'] = gw
    
    entry_pick_d['event_transfers'] = entry_pick_t['entry_history']['event_transfers']
    entry_pick_d['event_transfers_cost'] = entry_pick_t['entry_history']['event_transfers_cost']
    entry_pick_d['chip'] = entry_pick_t['active_chip']
    return(entry_pick_d)



def player_points_byW(week):
    week_dic = BSget('https://fantasy.premierleague.com/api/event/%s/live/' % week)
    week_df = pd.DataFrame(week_dic['elements'] , columns = ['id', 'explain']).copy()
    
    rows = []

    for i in week_df.itertuples():
        id_t =  i.id
        i_j = i.explain
        
        for j in i_j:
            fix_t = j['fixture']
            i_j_k = j['stats']
            
            for k in i_j_k:
                k['id2'] = id_t
                k['fixture2'] = fix_t
                rows.append(k) 
                
    df = pd.DataFrame(rows)
    df['Week'] = week
    return(df)

@st.cache(suppress_st_warning=True) 
def fixtures_byW(gw):
    fixtures1 = pd.DataFrame(BSget(f'https://fantasy.premierleague.com/api/fixtures/?event={gw}'))
    fixture2 = fixtures1[['id', 'event', 'finished', 'finished_provisional', 'kickoff_time', 'minutes', 'started']]
    return(fixture2)  
 
@st.cache(suppress_st_warning=True)                   
def GetManagerPoints(manager_id, gw):
    picks1 = get_entry_picks(manager_id, gw)

    bigtab1 = pd.merge(
        picks1, 
        points1,
        how ='left',
        left_on = ['element', 'Week'],
        right_on = ['id2', 'Week'],
        )
    
    bigtab1['true_points'] = bigtab1['multiplier'] * bigtab1['points']
    
    bigtab2 = pd.merge(
        bigtab1, 
        fixture1,
        how ='left',
        left_on = ['fixture2', 'Week'],
        right_on = ['id', 'event'],
        ).drop(columns=['fixture2', 'id','event'])
    
    bigtab3 = pd.merge(
        bigtab2, 
        players_mini,
        how ='left',
        left_on = ['element'],
        right_on = ['id'],
        ).drop(columns=['id','code'])
    
    
    bigtab3_summary = bigtab3.groupby(['position', 'multiplier', 'is_captain', 'is_vice_captain',
           'Week', 'finished',
           'finished_provisional', 'kickoff_time', 'started',
           'first_name', 'second_name', 'web_name'])['points', 'true_points'].sum().reset_index()
    
    
    
    FinalTable = pd.DataFrame(index=[manager_id])
    
    FinalTable['TotalPoints'] = bigtab3.true_points.sum()
    FinalTable['ConfirmedPoints'] = bigtab3.query('finished').true_points.sum()
    FinalTable['Captain'] = bigtab3.query('is_captain').web_name.values[0]
    FinalTable['Captain_Points'] = bigtab3.query('is_captain').points.sum()
    FinalTable['ViceCaptain'] = bigtab3.query('is_vice_captain').web_name.values[0]
    FinalTable['ViceCaptain_Points'] = bigtab3.query('is_vice_captain').points.sum()
    
    FinalTable['event_transfers'] = bigtab3['event_transfers'].values[0]
    FinalTable['event_transfers_cost'] = bigtab3['event_transfers_cost'].values[0]
    FinalTable['chip'] = bigtab3['chip'].values[0]
    FinalTable['BenchPoints'] = bigtab3.query('multiplier ==0').points.sum()
    FinalTable['Players Started'] = bigtab3.query('multiplier > 0 & started')['element'].nunique()
    FinalTable['Points per Player'] = FinalTable['TotalPoints']/FinalTable['Players Started']
    
    FinalTable['Player Blanks'] = bigtab3_summary.query('multiplier > 0 & started & points <= 3')['position'].nunique()
    
    FinalTable['Top Player'] = bigtab3_summary.sort_values('true_points', axis=0, ascending=False).web_name.values[0]
    FinalTable['Top Player Points'] = bigtab3_summary.sort_values('true_points', axis=0, ascending=False).points.values[0]
    return(FinalTable)

@st.cache(suppress_st_warning=True)  
def GetManagerPoints_league(leagueid, gw):
    league_d = BSget('https://fantasy.premierleague.com/api/leagues-classic/%s/standings' % leagueid)
    league_entries = pd.DataFrame(league_d['standings']['results'])['entry'].unique()
    
    league_season = pd.DataFrame()
    
    for entryid in league_entries:
        league_season = league_season.append(GetManagerPoints(entryid, gw))
        
    league_season['LeagueName'] = league_d['league']['name']
      
    league_entry_names = pd.DataFrame(league_d['standings']['results'])[['entry', 'entry_name', 'player_name']]
    
    league_season2 = pd.merge(
        league_season.reset_index(), 
        league_entry_names,
        how ='left',
        left_on = 'index',
        right_on = 'entry',
        ).drop(columns = ['index', 'entry']).set_index(['entry_name', 'player_name'])

    
    return(league_season2)                   
#%% Start



temp1 = BSgetStatic()
players_df = temp1[0]
events_df = temp1[1]

current_event_id = events_df.query('is_current == True')['id'].values[0]

players_mini = players_df[['id', 'first_name', 'second_name', 'code', 'web_name']].copy()

st.title("BS Fantasy Football")

st.header('Event Details')

#%% Player Details

with st.beta_expander('%s Top Players:' % events_df.query('is_current')['name'].item()):
    
    col1a, col1b, col2a, col2b ,col3a, col3b,col4a, col4b,col5a, col5b, = st.beta_columns(10)
    
    col1a.markdown(GetPlayer1MD('Selected', 'most_selected')[0])
    col1b.image(GetPlayer1MD('Selected', 'most_selected')[1])
    
    col2a.markdown(GetPlayer1MD('Transferred In', 'most_transferred_in')[0])
    col2b.image(GetPlayer1MD('Transferred In', 'most_transferred_in')[1])
    
    col3a.markdown(GetPlayer1MD('Captained', 'most_captained')[0])
    col3b.image(GetPlayer1MD('Captained', 'most_captained')[1])
    
    col4a.markdown(GetPlayer1MD('Vice-Captained', 'most_vice_captained')[0])
    col4b.image(GetPlayer1MD('Vice-Captained', 'most_vice_captained')[1])
    
    col5a.markdown(GetPlayer1MD('Points', 'TopPlayer')[0])
    col5b.image(GetPlayer1MD('Points', 'TopPlayer')[1])
    

    
#%% Chip Usage

#Icon Options #https://pastebin.com/raw/w0z7d5Wh
#st.markdown(':arrow_up_small: :arrow_down_small: :arrow_up: :arrow_down: :point_up_2: :point_down:')

with st.beta_expander('%s Chip Usage:' % events_df.query('is_current')['name'].item()):
    coltc, colbb, colfh, colwc  = st.beta_columns(4)       
        
    coltc.markdown(ChipMD('Triple Captain', '3xc'))
    colbb.markdown(ChipMD('Bench Boost', 'bboost'))
    colfh.markdown(ChipMD('Freehit', 'freehit'))
    colwc.markdown(ChipMD('Wildcard', 'wildcard'))

                
#%% 
st.header('League Data')

fixture1 = fixtures_byW(current_event_id)
points1 = player_points_byW(current_event_id)

my_expander = st.beta_expander("Data Load", expanded=True)
with my_expander:
    league_id = st.text_input('Enter League ID', '236821')
    data_load_state = st.text('Loading data...')
    WeekData = GetManagerPoints_league(league_id, current_event_id)
    data_load_state.text('Loading data...done! Check out the %s league' % WeekData['LeagueName'].unique()[0])

st.dataframe(WeekData)

