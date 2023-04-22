import pandas as pd
import json
import os 

import random
from bs4 import BeautifulSoup

import yfinance as yf
import requests



# 公司盈利数据链接
# revenue_link = 'https://www.macrotrends.net/stocks/charts/AAPL/apple/revenue'



# 分析某个行业利润增长与股票增长的相关性
def sector_analysis(sector_name:str, sample_amount:int):
    """
    :param sector_name: 这个sector的名称，有这些sector可供选择 Materials , Energy , Industrials , Consumer_Discretionary , Consumer_Staples , Health_Cares , Financials , Information_Technology , Communication_Services , Utilities , Real_Estate
    :param sample_amount: 在这个sector里面取样本的数量，建议保持在10个以下
    :return: 这些公司的利润增长与股票增长的相关性均值
    """
    # 准备工作
    result_list = [] # 创建一个用于存储指标的列表
    stock_tickers = _sector_pick(sector_name, sample_amount) # 抽取对应数量的公司Ticker

    # 获取每个公司的相关性指标
    for i in stock_tickers:
        print(i)
        indicator_value =  get_relative_indicator(i)
        # 如果这个公司没有相应的数据的话，进行下一个公司的查找
        if indicator_value is None:
            continue
        result_list.append(indicator_value)

    # 将每个公司的相关性指标取均
    relative_indicator_mean = sum(result_list) / len(result_list)

    # 返回相关性指标均值
    return relative_indicator_mean

# 得到公司季度Revenue
def get_quarterly_revenue(stock_ticker:str):
    """
    :param stock_ticker: 公司股票ticker
    :return: 返回装有该公司季度revenue的dataframe
    """

    stock_name = _ticker_to_name(stock_ticker)
    if stock_name is None: # 如果为None的话代表没有对应的Revenue数据
        return None
    current_dir = os.path.dirname(os.path.abspath(__file__)) # 获取该python文件在用户电脑的绝对位置
    revenue_folder_buffer_path = os.path.join( current_dir , 'data_buffer' )
    revenue_file_buffer_path = os.path.join( current_dir , 'data_buffer' , f'{stock_ticker}.csv')
    
    # 如果没有数据的话就去服务器申请，有数据的话就从本地提
    if not os.path.exists(revenue_file_buffer_path):
        # print(f'在服务器申请{stock_name}数据中..')
        # 爬虫：先分别获取股票的盈利增长数据，并存在本地的csv中 (本地里有的就不需要去获取了)
        url = f'https://www.macrotrends.net/stocks/charts/{stock_ticker}/{stock_name}/revenue'
        source = requests.get(url).content
        soup = BeautifulSoup(source,'html.parser')

        # 获得网页Revenue的Table分组
        useful = soup.find(attrs={'id':'style-1'})
        tables = useful.find_all('table')

        # 创建空列表用于季度Revnue数据
        data = []

        # 放入季度Revnue数据
        for row in tables[1].find_all('tr'):
            columns = row.find_all('td')
            if columns:
                date = columns[0].text.strip()
                revenue = columns[1].text.strip()
                if revenue == '':
                    continue
                data.append((date, revenue))

        # 将季度Revnue数据放入一个dataframe并存到本地文件夹，下次就不用再去人家的服务器申请
        df = pd.DataFrame(data, columns=['date', 'revenue'])
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df['revenue'] = df['revenue'].str.replace('$', '', regex=False).str.replace(',', '').astype(float)
        if df.empty:
            return None

        # 如果没文件夹的话就创建一个文件夹，有就直接存到文件夹内
        if not os.path.isdir(revenue_folder_buffer_path):
            os.mkdir('data_buffer')
            df.to_csv(revenue_file_buffer_path, index=True)
        else:
            df.to_csv(revenue_file_buffer_path, index=True)

        return df

    # 如果本地有数据的话就从本地提取返回
    # print(f'在本地读取{stock_name}数据中..')
    df = pd.read_csv(revenue_file_buffer_path)
    df.set_index('date', inplace=True)
    return df

# 得到单个公司的分析情况的dataframe
def get_company_analysis_df(stock_ticker:str):

    # 获得公司的季度revenue的dataframe
    revenue_df = get_quarterly_revenue(stock_ticker)
    if revenue_df is None: # 如果没有对应的Revenue数据的话，返回None
        return None


    # 从雅虎财经中得到对应季度revenue日期的股票价格数据
    stock_info = yf.Ticker(stock_ticker) 
    stock_price_df = stock_info.history(period="max")  
    stock_price_df.index = stock_price_df.index.strftime('%Y-%m-%d') # 将日期列转换成datetime格式
    
    # 数据合并与处理
    merged_df = pd.merge(revenue_df, stock_price_df['Close'] ,left_index=True, right_index=True ,how='left') # 并合在一个dataframe中(使用left_join)，对这个dataframe进行pandas数据分析
    merged_df = merged_df.rename(columns={'Close': 'stock_close'}) # 更改列名字
    idx = merged_df[merged_df['stock_close'].isna()].index # 找出包含NaN值的行的index
    
    for i in idx:  # nan值可能代表股票在那一天不开盘，可能是周六周日，于是乎我找个最接近nan row的日期，且股票在那天开盘的close，然后替代nan的值。
        closest_date = stock_price_df.index[stock_price_df.index >= str(i)].min()  # 找出大于nan row日期的所有日期，取最小值，也就是取最接近nan row日期后有股票数据的日期。
        closest_close = stock_price_df.loc[closest_date, 'Close']  # 通过这个最近的日期，找到这个最近的日期的close值
        merged_df.loc[i, 'stock_close'] = closest_close  # 替代我们nan值

    merged_df = merged_df.sort_index(ascending=True) # 重新排序日期，按索引降序排序，最早的日期会在最前面
    merged_df['revenue_chg'] = merged_df['revenue'].pct_change() # 增加revenue变化百分比列
    merged_df['stock_close_chg'] = merged_df['stock_close'].pct_change() # 增加close变化百分比列

    # 数据逻辑进行判断 (当growth_rate在增长的时候(今年的growth大于前年的growth)，股票价格是否增长(收益是否大于0))
    merged_df['revenue_vs_stock_close'] = '' # 创建一个空列
    try:
        merged_df.loc[(merged_df['revenue_chg'] > merged_df['revenue_chg'].shift(1)) & (merged_df['stock_close_chg'] > 0), 'revenue_vs_stock_close'] = 'Both_Up' # 如果growth增长，股票也增加，那么显示'Both_Up'
        merged_df.loc[(merged_df['revenue_chg'] < merged_df['revenue_chg'].shift(1)) & (merged_df['stock_close_chg'] < 0), 'revenue_vs_stock_close'] = 'Both_Down' # 如果growth下跌，股票也下跌，那么显示'Both_Down'
        merged_df.loc[(merged_df['revenue_chg'] > merged_df['revenue_chg'].shift(1)) & (merged_df['stock_close_chg'] < 0), 'revenue_vs_stock_close'] = 'RevenueGrowth_StockDown' # 如果growth增长，股票也下降，那么显示'RevenueGrowth_StockDown'
        merged_df.loc[(merged_df['revenue_chg'] < merged_df['revenue_chg'].shift(1)) & (merged_df['stock_close_chg'] > 0), 'revenue_vs_stock_close'] = 'StockGrowth_RevenueDown' # 如果growth下降，股票也上升，那么显示'StockGrowth_RevenueDown'
    except KeyError: # 数据太少就会造成KeyError，因此我们决定忽略这家公司，返回None
        return None
    # 返回公司数据分析后的dataframe
    return merged_df

# 得到自定义的相关性指标
def get_relative_indicator(stock_ticker:str):

    # 获取公司分析后的dataframe
    merged_df = get_company_analysis_df(stock_ticker)
    if merged_df is None: # 如果值为None代表没有对应的数据
        return None

    # 定义相关指标 (Both_Up + Both_Down) / (Both_Up + Both_Down + StockGrowth_RevenueDown + RevenueGrowth_StockDown)
    try:
        both_up_count = merged_df['revenue_vs_stock_close'].value_counts()['Both_Up']
        both_down_count = merged_df['revenue_vs_stock_close'].value_counts()['Both_Down']
        Rup_Sdown_count = merged_df['revenue_vs_stock_close'].value_counts()['RevenueGrowth_StockDown']
        Sup_Rdown_count = merged_df['revenue_vs_stock_close'].value_counts()['StockGrowth_RevenueDown']
        relative_indicator = (both_up_count+both_down_count)/(both_up_count+both_down_count+Rup_Sdown_count+Sup_Rdown_count)
    except KeyError: # 数据太少就会造成KeyError，因此我们决定忽略这家公司，返回None
        return None

    # 返回自定义的相关性指标
    return relative_indicator

# 随机抽取一个装有指定Sector的公司ticker样本列表
def _sector_pick(sector_name:str, sample_amount:int):
    """
    :param sector_name: 选项有 Materials , Energy , Industrials , Consumer_Discretionary , Consumer_Staples ,
    Health_Cares , Financials , Information_Technology , Communication_Services , Utilities , Real_Estate，请随意选取一个
    :param sample_amount: 打算抽样的公司数量
    :return: 返回一个装有指定数量的公司股票Ticker列表
    """
    current_dir = os.path.dirname(os.path.abspath(__file__)) # 获取该python文件在用户电脑的绝对位置
    sector_tickers_path = os.path.join(current_dir,'pre_required','sector_tickers.csv')

    df = pd.read_csv(sector_tickers_path)
    df = df.fillna('')  # 将nan数据变成''空字符创
    ticker_list = df[f'{sector_name}'].tolist()  # 装有该Sector下所有股票Ticker的列表
    ticker_list = list(filter(lambda x: x != '', ticker_list))  # 清除列表里所有的空字符串元素

    # 返回列表
    return random.sample(ticker_list, sample_amount)

# 爬虫私用 - 返回公司ticker所对应的用于爬虫的名字
def _ticker_to_name(ticker:str):
    """
    :param ticker: 公司对应的ticker
    :return: 返回用于爬虫的名字
    """
    # Json文件源： https://www.macrotrends.net/stocks/charts/JNJ/johnson-johnson/revenue 内网页右上角点击搜索以后，控制台XHR捕抓到的 https://www.macrotrends.net/assets/php/ticker_search_list.php?_=1682026428533 项目，我这里直接把Preview复制下来供爬虫程序运用。
    
    current_dir = os.path.dirname(os.path.abspath(__file__)) # 获取该python文件在用户电脑的绝对位置
    ticker_search_list_path = os.path.join(current_dir,'pre_required','ticker_search_list.json')

    # 读取Json文件，并将对应的数据整理到一个字典内。
    with open(ticker_search_list_path,'r') as f:
        data = json.load(f) 
        result_dict = {item['s'].split('/')[0]: item['s'].split('/')[1] for item in data}
    
    # 从字典读取对应的用于爬虫的名字 (如果没有对应的ticker的话，返回None)
    try:
        return result_dict[ticker]
    except KeyError:
        return None


# 主程序
if __name__ == "__main__":
    
    # 行业选择有: Materials , Energy , Industrials , Consumer_Discretionary , Consumer_Staples , Health_Cares , Financials , Information_Technology , Communication_Services , Utilities , Real_Estate
    print(sector_analysis('Energy', 10))  # 选取'Energy'行业，从中抽取10个归类为'Energy'行业的公司，然后输出他们的利润增长与股票增长的相关性均值

   