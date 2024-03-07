import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import time
from clean_data import process_data
from functions import *

# set the page
st.set_page_config(page_title="话单行迹生成", layout="wide")

# initialization
if 'handled_file' not in st.session_state:   # indicate the file uploaded is handled or not
    st.session_state['handled_file'] = False
if 'df_final' not in st.session_state:   # keep the handled data
    st.session_state['df_final'] = 'NA'
if 'have_data' not in st.session_state:   # indicate if df_final has the handled data
    st.session_state['have_data'] = False
if 'traj_generated' not in st.session_state:   # indicate if the generate_traj button has been clicked
    st.session_state['traj_generated'] = False
if 'upload_button_clicked' not in st.session_state:   # indicate if the upload-file button has been clicked
    st.session_state['upload_button_clicked'] = False
def on_upload_button_clicked():
    st.session_state['upload_button_clicked'] = True
if 'download_button_clicked' not in st.session_state:   # indicate if the download-file button has been clicked
    st.session_state['download_button_clicked'] = False
def on_download_button_clicked():
    st.session_state['download_button_clicked'] = True


if st.session_state['have_data'] == False:
    st.title("话单轨迹呈现")
    
    st.warning("如果您上传的话单数据文件为未处理过的, 请确保文件中存在'己方号码'、'截获时间'、'呼叫类型'、'对方号码'、'己方位置区'、'己方小区'这6个列名。\
               上传未处理的文件后会生成一个处理后的csv文件, 请按下载按钮下载并妥善保存, 该文件名为原文件名后加上'_handled'。\
               之后的使用请优先上传处理后的文件。")
    st.warning('由于lbs转换经纬度的接口限制, 本程序每天处理原始数据的记录数量上限为10000条, 建议单次处理原始数据的记录数量不超过5000条。如果是使用处理后的数据, 则无使用限制。')

    # upload file
    uploaded_file = st.file_uploader("上传话单文件", type=["csv", "xlsx"])
    st.button("上传", on_click=on_upload_button_clicked)

    if (uploaded_file is not None) and (st.session_state['upload_button_clicked'] == True):
        file_name = uploaded_file.name   # get the name of the file
        
        # check if the file has been handled, if handled, read directly
        handled = check_handled_file(file_name)
        if handled == True:
            st.session_state['handled_file'] = True

        # read and handle original data and save as a new csv file
        if st.session_state['handled_file'] == False:
            if st.session_state['download_button_clicked'] == False:
                st.warning("正在处理数据, 请稍等...")
                df_final = process_data(uploaded_file=uploaded_file, file_name=file_name)

                st.session_state['df_final'] = df_final

                # save handled data
                file_name_suffix_rmed = remove_suffix(file_name)   # remove suffix of the file name
                down = st.download_button(
                    label="下载处理后的数据",
                    data=df_final.to_csv(index=False).encode('utf-8'),
                    file_name=f"{file_name_suffix_rmed}_handled.csv",
                    mime='text/csv',
                    on_click=on_download_button_clicked
                )
            elif st.session_state['download_button_clicked'] == True:
                st.success("数据下载成功, 进入轨迹生成页面...")
                time.sleep(3)
                st.session_state['have_data'] = True
                st.rerun()
        else:
            df_final = pd.read_csv(uploaded_file)
            st.session_state['df_final'] = df_final
            
            st.success("数据读取成功, 进入轨迹生成页面...")
            time.sleep(3)
            st.session_state['have_data'] = True
            st.rerun()

elif st.session_state['have_data'] == True:
    data = st.session_state['df_final']
    
    # change the data types of some columns
    change_col_list = ['己方号码', '对方号码', '己方位置区', '己方小区', '己方卡号', '己方机身码']
    for col in change_col_list:
        if col in data.columns:
            data[col] = data[col].fillna(0).astype(np.int64).astype(str)
            data[col] = data[col].replace('0', pd.NA)
    data['截获时间'] = pd.to_datetime(data['截获时间'])
    
    # create one dataframe for the valid data and one for the unvalid data
    data_no_nan = data.dropna(subset=['纬度', '经度'])
    data_unvalid = data[~data.index.isin(data_no_nan.index)]

    # get the list of phones included in the data
    phone_list = list(data_no_nan['己方号码'].unique())

    # create the list of call types
    call_type_list = ['主叫', '被叫', '主短', '被短']

    # create the list of maps
    map_list = list(map_dict.keys())
    
    with st.sidebar:
        st.header('**构建话单行迹图的条件筛选:**')

    phone_selected = st.sidebar.multiselect("选择要查询的手机号码", phone_list, default=phone_list)

    if phone_selected == []:
        st.sidebar.error('请选择电话。')
    else:
        # get and show the time range of valid data with specific phone number
        earliest_time_with_phone_selected = data_no_nan.loc[data_no_nan['己方号码'].isin(phone_selected), '截获时间'].min()
        latest_time_with_phone_selected = data_no_nan.loc[data_no_nan['己方号码'].isin(phone_selected), '截获时间'].max()
        st.sidebar.write(f'所选号码最早的截获时间: {earliest_time_with_phone_selected}  \n所选号码最晚的截获时间: {latest_time_with_phone_selected}')
        
        earliest_time_with_phone_selected_tf = time.strptime(str(earliest_time_with_phone_selected), "%Y-%m-%d %H:%M:%S")
        latest_time_with_phone_selected_tf = time.strptime(str(latest_time_with_phone_selected), "%Y-%m-%d %H:%M:%S")
    
    # datetime selection block
    sidecol1, sidecol2 = st.sidebar.columns([1,1], gap='medium')
    with sidecol1:
        start_date_selected = st.date_input('选择起始日期')
        end_date_selected = st.date_input('选择结束日期')
    with sidecol2:
        start_time_selected = st.time_input('选择起始时间')
        end_time_selected = st.time_input('选择结束时间')
    
    # merge selected date and time
    start_datetime_selected = str(start_date_selected) + ' ' + str(start_time_selected)
    end_datetime_selected = str(end_date_selected) + ' ' + str(end_time_selected)
    start_datetime_selected_tf = time.strptime(start_datetime_selected, "%Y-%m-%d %H:%M:%S")
    end_datetime_selected_tf = time.strptime(end_datetime_selected, "%Y-%m-%d %H:%M:%S")
    
    # check time input
    if phone_selected != []:
        if start_datetime_selected_tf > end_datetime_selected_tf:
            st.sidebar.error('起始时间不能晚于结束时间!')
       
    # multiselect for call types
    call_type_selected = st.sidebar.multiselect("请选择呼叫类型", call_type_list, default=call_type_list)
    
    # multiselect for map types
    map_selected = st.sidebar.selectbox("选择地图类型: ", map_list)

    # create a slifer for the line opacity
    line_opacity = st.sidebar.slider('选择轨迹线透明度', 0.0, 1.0, 1.0)

    # button for generate the final map
    generate_traj = st.sidebar.button('生成轨迹图')

    # colormap for different phone number
    colors = colors_ava[:len(phone_list)]
    phone_color_dict = {phone: color for phone, color in zip(phone_list, colors)}

    # the setting for updating the traj
    if st.session_state['traj_generated'] == False:
        if (generate_traj == True) & (phone_selected != []):
            st.session_state['traj_generated'] = True
    if (st.session_state['traj_generated'] == True) & (phone_selected != []):
        # update the traj
        traj, record_dict = plot_trajectories(data_no_nan, phone_selected, phone_color_dict, start_time=start_datetime_selected, end_time=end_datetime_selected, 
                                call_types=call_type_selected, tiles=map_dict[map_selected], map_attr=map_selected, line_opacity=line_opacity)
        map_html = traj._repr_html_()
        components.html(map_html, height=800)

        for key, value in record_dict.items():
            st.write(f"所选拦截时间段内，关于号码{key}的记录有{value}条。")

        st.header('全部数据的处理结果：')
        # show basic information for all data
        num_all_record = len(data.index)
        num_region_na = data['己方位置区'].isna().sum()
        num_comm_na = data['己方小区'].isna().sum()
        num_errcode_0 = len(data[data['错误']=='无'])
        num_errcode_10000 = len(data[data['错误']=='参数错误'])
        num_errcode_10001 = len(data[data['错误']=='无查询结果'])
        num_errcode_nan = data['错误'].isna().sum()
        num_all_unvalid = num_errcode_10000 + num_errcode_10001 + num_errcode_nan
        st.write(f"\n\n- 共有记录{num_all_record}条;\
                 \n- 转换坐标成功{num_errcode_0}条, 即能显示位置的记录数量;\
                 \n- 无法显示位置的记录数为{num_all_unvalid}条; 转换坐标参数错误{num_errcode_10000}条; 转换坐标无查询结果{num_errcode_10001}条; 转换坐标结果缺失{num_errcode_nan}条")

        if st.checkbox('显示所有数据（包含有效和无效）'):
            st.write('以下表中的空白表示缺失数据')
            create_interactive_df(data)

        if st.checkbox('显示所有有效数据'):
            data_temp_1 = data_no_nan.reset_index(drop=True)
            st.write('以下表中的空白表示缺失数据')
            create_interactive_df(data_temp_1)
            

        if st.checkbox('显示所有无效数据'):
            data_temp_2 = data_unvalid.reset_index(drop=True)
            st.write('以下表中的空白表示缺失数据')
            create_interactive_df(data_temp_2)
            st.write("无效数据类型:  \n \
                     1.己方社区或己方位置区数据存在缺失  \n \
                     2.转换为经纬度时参数错误(在'错误'列呈现为'参数错误')  \n \
                     3.转换为经纬度时无查询结果(在'错误'列呈现为'无查询结果')")





        
        

