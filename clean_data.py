import pandas as pd
import numpy as np
import chardet
import requests
import streamlit as st

@st.cache_data
def process_data(uploaded_file, file_name):
    # read data by file type
    df = read_data_by_file_type(uploaded_file, file_name)

    # clean data
    df_cln = clean_data(df)

    # get location information
    df_final = get_loc(df_cln)

    return df_final



# read data by file type
def read_data_by_file_type(uploaded_file, file_name):
    # check the uploaded file encoding
    result = chardet.detect(uploaded_file.read())
    uploaded_file.seek(0)
    encoding = result['encoding']

    # deal with GB2312 encoding as GBK
    if encoding == "GB2312":
        encoding = "GBK"
    else:
        encoding = "UTF-8"

    # read data by file type and encoding
    if file_name.endswith("csv"):
        df = pd.read_csv(uploaded_file, encoding = encoding)
    elif file_name.endswith("xlsx") or file_name.endswith("xls"):
        df = pd.read_excel(uploaded_file, sheet_name=0)

    return df



# clean data
def clean_data(df):
    # remove * in column names
    df.columns = [col.replace("*", "") for col in df.columns]

    # extract useful columns
    basic_cols = ['己方号码', '截获时间', '呼叫类型', '对方号码', '己方位置区', '己方小区']
    other_cols = ['己方卡号', '己方机身码', '时长', '己方姓名', '对方姓名']
    all_cols = basic_cols
    for col in other_cols:
        if col in df.columns:
            all_cols.append(col)
    print(f"成功提取变量{[col for col in all_cols]}")
    
    # remove \t and handle blank spaces
    df_2 = df[all_cols].copy()
    for col in df_2.select_dtypes(include = "object").columns:
        df_2[col] = df_2[col].str.replace("\t", '').copy()
        df_2[col] = df_2[col].replace("", np.nan).copy()

    # for '己方位置区' and '己方小区', change 0 to nan
    df_3 = df_2.copy()
    for col in ['己方位置区', '己方小区']:
        df_3[col] = df_3[col].astype(str)
        df_3[col] = df_3[col].str.strip().replace('0', np.nan)
        df_3[col] = df_3[col].replace('nan', np.nan)
    num_nan_loc = df_3['己方位置区'].isna().sum()
    num_nan_dis = df_3['己方小区'].isna().sum()
    print("己方位置区为缺失值的记录数: ", num_nan_loc)
    print("己方小区为缺失值的记录数: ", num_nan_dis)

    return df_3
    


# only transfer lbs to coordinate
def lbs_to_coord(df, mnc=0):
    for i in range(min(df.index), max(df.index)+1):
        print("\r已经完成{}条定位信息".format(i), end="")
        lac = df.loc[i, '己方位置区']
        ci = df.loc[i, '己方小区']
        url = "http://vip.cellocation.com/cell/effgdsil.php?mcc=460&mnc={}&lac={}&ci={}".format(mnc, lac, ci) 

        # send requests
        response = requests.get(url)

        # get the result
        result = response.json()

        df.loc[i, '错误'] = result['errcode']
        df.loc[i, '纬度'] = result['lat']
        df.loc[i, '经度'] = result['lon']
        df.loc[i, '精度半径'] = result['radius']
        df.loc[i, '地址'] = result['address']
    
    return df



# get location information
def get_loc(df):
    df_uniq = df[['己方位置区', '己方小区']].value_counts()
    df_uniq = df_uniq.reset_index()
    df_uniq.drop('count', axis=1, inplace=True)
    
    df_coord = lbs_to_coord(df_uniq.loc[:, :])

    df_final = pd.merge(df, df_coord, how='left', on=['己方位置区', '己方小区'])

    # change dtypes of latitude, longitude and longitude radius to float
    df_final['经度'] = df_final['经度'].astype(float)
    df_final['纬度'] = df_final['纬度'].astype(float)
    df_final['精度半径'] = df_final['精度半径'].astype(float)

    # change 0 of latitude, longitude and longitude radius to nan
    df_final['经度'] = df_final['经度'].replace(0, np.nan)
    df_final['纬度'] = df_final['纬度'].replace(0, np.nan)
    df_final['精度半径'] = df_final['精度半径'].replace(0, np.nan)

    # change blank spaces in address to nan
    df_final['地址'] = df_final['地址'].replace('', np.nan)

    # change errcode as str
    df_final['错误'] = df_final['错误'].fillna(-1).astype(int)
    df_final['错误'] = df_final['错误'].astype(str)
    df_final['错误'] = df_final['错误'].replace('0', '无')
    df_final['错误'] = df_final['错误'].replace('10000', '参数错误')
    df_final['错误'] = df_final['错误'].replace('10001', '无查询结果')
    df_final['错误'] = df_final['错误'].replace('-1', np.nan)
    num_0 = len(df_final[df_final['错误']=='无'])
    num_10000 = len(df_final[df_final['错误']=='参数错误'])
    num_10001 = len(df_final[df_final['错误']=='无查询结果'])
    num_nan = df_final['错误'].isna().sum()
    # 错误类别: 0为无错误, 10000为参数错误, 10001为无查询结果"
    print("转换成功{}条\n参数错误{}条\n无查询结果{}条\n缺失{}条".format(num_0, num_10000, num_10001, num_nan))

    # change data type of getting time to datatime
    df_final['截获时间'] = pd.to_datetime(df_final['截获时间'])

    return df_final
