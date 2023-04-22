`项目介绍`

我认为单从盈利数据而不考虑经济环境的情况下，公司盈利的增长应该与跟股票的涨跌会有相关性，而我对相关性的定义如下：


$$
\small \frac{同时上涨次数+同时下跌次数}{同时上涨次数+同时下跌次数+一个上涨一个下跌的次数}
$$


如果这个数值大于0.5很多的话，那就代表盈利的增长与跟股票的涨跌会有相关性。我在主目录的"Rev_EPS_Analysis.xlsx"文件中有示例，随机挑了两个科技行业的样本：谷歌与苹果，谷歌看起来没什么相关性，苹果看起来有一些相关性。所以我就打算利用程序测试一下我的想法。

---

`代码使用介绍`

运行一下 `main.py`文件就好了，还有里面除了_下划线开头的私有函数以外，其它函数也可以按规则进行调用，包括：

```python
# 1. 输入股票代码即可得到一个带有历史季度利润的dataframe
get_quarterly_revenue(stock_ticker) 

# 2. 输入股票代码即可得到一个使用我这种方法进行分析详细的dataframe
get_company_analysis_df(stock_ticker)

# 3. 输入股票代码即可得到该公司对应的盈利与股票增长的相关性
get_relative_indicator(stock_ticker)

```


---

**`粗略测试结果`**

我使用了程序在每个行业中随机获取十支股票代码，然后测试他们的相关性均值，下面是结果：

|          行业          | 相关性均值 |
| :--------------------: | :--------: |
|       Materials       |    0.56    |
|         Energy         |    0.46    |
|      Industrials      |    0.48    |
| Consumer Discretionary |    0.46    |
|    Consumer Staples    |    0.52    |
|      Health Cares      |    0.51    |
|       Financials       |    0.48    |
| Information Technology |    0.5    |
| Communication Services |    0.48    |
|       Utilities       |    0.48    |
|      Real Estate      |    0.54    |

---

`打算`

在每个行业里抽取更多不同的样本做一个Hypothesis Testing，看看是否某个行业盈利会与股票涨跌有相关性。
