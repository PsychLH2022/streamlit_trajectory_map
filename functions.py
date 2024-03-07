import pandas as pd
import numpy as np
import streamlit as st
import datetime
import folium
from folium.plugins import MarkerCluster
from st_aggrid import AgGrid, GridOptionsBuilder

# dictionary for map tiles and attributes
map_dict = {"高德-常规图": 'http://wprd02.is.autonavi.com/appmaptile?x={x}&y={y}&z={z}&lang=zh_cn&size=1&scl=1&style=7',
            "高德-卫星图": 'http://wprd02.is.autonavi.com/appmaptile?x={x}&y={y}&z={z}&lang=zh_cn&size=1&scl=1&style=6'}



# list of colors avaliable
colors_ava = ['green', 'cadetblue', 'purple', 'beige', 'lightgray', 'darkblue', 
              'lightred', 'red', 'darkgreen', 'pink', 'orange', 'white', 
              'lightgreen', 'black', 'darkpurple', 'darkred', 'gray', 'blue', 'lightblue']



# remove suffix of the file name
def remove_suffix(file_name):
    if file_name.endswith('.csv'):
        file_name_suffix_rmed = file_name.replace('.csv', '').strip()
    elif file_name.endswith('.xlsx'):
        file_name_suffix_rmed = file_name.replace('.xlsx', '').strip()
    elif file_name.endswith('.xls'):
        file_name_suffix_rmed = file_name.replace('.xls', '').strip()

    return file_name_suffix_rmed



# check if the file has been handled
def check_handled_file(file_name):
    # check if the file name includes '_handled.csv'
    if file_name.endswith('_handled.csv'):
        result = True
    else:
        result = False
    
    return result



# get the max and min time with datetime form
def get_max_min_time(d):
    datetime_str = str(d)
    datetime_obj = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    date_part = datetime_obj.date()
    time_part = datetime_obj.time()

    return date_part, time_part



@st.cache_resource
# create the location plot
def plot_trajectories(df, person_phones, phone_color_dict, start_time, end_time, call_types=['主叫', '被叫', '主短', '被短'], line_opacity=1, 
                        tiles='http://wprd02.is.autonavi.com/appmaptile?x={x}&y={y}&z={z}&lang=zh_cn&size=1&scl=1&style=7', 
                        map_attr='高德-常规图', start_size=13):
    # make sure person_phones is a list
    if isinstance(person_phones, str):
        person_phones = [person_phones]

    # make sure call_types is a list
    if isinstance(call_types, str):
        call_types = [call_types]

    # create a dataframe for selected phone numbers
    phones_df = df[df['己方号码'].isin(person_phones)]
    if phones_df.empty:
        print("没有找到符合条件的数据。")
        return
    
    # filter by selected time range
    df_filter_by_time = phones_df[(phones_df['截获时间'] >= start_time) & (phones_df['截获时间'] <= end_time)]

    # filter by selected call types
    df_filter_by_time_calltypes = df_filter_by_time[df_filter_by_time['呼叫类型'].isin(call_types)]

    # ensure a map center using their location data
    map_center = [phones_df['纬度'].mean(), phones_df['经度'].mean()]
    map = folium.Map(location=map_center, tiles=tiles, attr=map_attr, zoom_start=start_size)
    
    # create a object of MarkerCluster
    maker_cluster = MarkerCluster().add_to(map)   

    # create a empty dict for phone and the number of found records
    num_record_by_phone_dict = {}
    
    for phone in person_phones:
        # filter data of selected phone
        df_filtered_final = df_filter_by_time_calltypes[df_filter_by_time_calltypes['己方号码'] == phone]
        num_record = len(df_filtered_final)
        num_record_by_phone_dict[str(phone)] = num_record

        # create a dictionary whose key is the time and value is the location
        loc_dict = {}
        for j, row in df_filtered_final.iterrows():
            loc_dict[row['截获时间']] = [row['纬度'], row['经度']]
        
        # sort the dictionary by time
        loc_dict = dict(sorted(loc_dict.items()))
        list_loc = list(loc_dict.values())
        
        # create a list of trajs between two locations
        trajectorys = []
        for k in range(len(list_loc)-1):
            trajectorys.append([list_loc[k], list_loc[k+1]])
        
        # add trajs on the map
        for trajectory in trajectorys:
            folium.PolyLine(trajectory, color=phone_color_dict[phone], weight=3, opacity=line_opacity).add_to(maker_cluster)
        
        # the html script for add note for each maker
        for j, (_, row) in enumerate(df_filtered_final.iterrows()):
            html_content = f"""
            <div>
                <strong>己方号码:</strong> {phone}<br>
                <strong>截获时间:</strong> {row['截获时间']}<br>
                <strong>呼叫类型：</strong>{row['呼叫类型']}<br>
                <strong>对方号码：</strong>{row['对方号码']}<br>
                <strong>地址: </strong>{row['地址']}
            </div>
            """
            
            # create makers
            folium.Marker([row['纬度'], row['经度']], 
                          icon=folium.Icon(color=phone_color_dict[phone], prefix='fa', icon='phone'), 
                          popup=folium.Popup(folium.Html(html_content, script=True), max_width=350),
                          tooltip=f'截获时序点{j+1}').add_to(maker_cluster)
        
    # show the map
    return map, num_record_by_phone_dict



# create an interactive dataframe
def create_interactive_df(df):
    builder = GridOptionsBuilder.from_dataframe(df)
    builder.configure_default_column(groupable=True)
    builder.configure_side_bar()
    builder.configure_pagination(paginationAutoPageSize=False, paginationPageSize=50)
    AgGrid(df,
           gridOptions=builder.build(),
           custom_css={"#gridToolBar": {"padding-bottom": "0px !important"}},
           height=600,
           enable_quicksearch=True)