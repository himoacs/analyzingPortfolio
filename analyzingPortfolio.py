import pandas as pd                                               # Import pandas
from pandas.io.data import DataReader                             # Module for getting data from Yahoo
import datetime as dt
from dateutil import parser
from matplotlib import pyplot as plt
%matplotlib inline                                                
from pylab import rcParams                                        # Increase size of graph
rcParams['figure.figsize'] = 13, 5
import warnings                                                   # Hide warnings
warnings.filterwarnings('ignore')

# Read the transaction data from csv
transactions=pd.read_csv('/Users/himanshugupta/Documents/transactions.csv')

# Calculate inital cost of purchase for each stock
transactions['cost']=transactions['price']*transactions['quantity']

# Get today's date
today = dt.datetime.today().strftime("%Y%m%d")

# Get minimum transaction date
min_date = parser.parse(str(transactions.date_bought.min()))+dt.timedelta(days=1)

# Define a new dataframe to hold cash value
cs = transactions[transactions['stock']=='cash']
cs['value'] = cs['cost'] = cs['price']
cs['price'] = float('NaN')
    
# Function for getting list of dates
def daterange(start_date, end_date, step):
    for n in range(0,int((end_date - start_date).days),step):
        yield start_date + dt.timedelta(n)
        

# This function does daily analysis on the portfolio 

def pf_stats(single_date,transactions,min_date,flag):
        
    transactions = transactions[transactions['stock']!='cash']
    
    # Get a list of unique stocks in your portfolio
    unique_stocks = pd.unique(transactions.stock)

    # Get prices from Google Finance for each unique stock
    price={}
    for ticker in unique_stocks:
        price[ticker] = DataReader(ticker, "yahoo", str(min_date),single_date)
    
    # For each transaction, get the close price
    for index,row in transactions.iterrows():
        
        if (parser.parse(single_date)==parser.parse(str(int(row.date_bought)))):
            cs['value']-=int(row.cost)
        
        if pd.isnull(row.date_sold):
            transactions.loc[index,'status']='active'
            transactions.loc[index,'last_price']=price[row.stock].tail(n=1).Close.ix[0]
        else:
            transactions.loc[index,'status']='closed'
            # If the security hasn't been sold yet (but will be in future), then take last price
            # Once it is sold, take the price of the date it was sold
            if (single_date<=str(int(row.date_sold))):
                transactions.loc[index,'last_price']=price[row.stock].tail(n=1).Close.ix[0]
                
            elif (parser.parse(single_date)>parser.parse(str(int(row.date_sold)))):
                transactions.loc[index,'last_price']=price[row.stock].Close.loc[str(int(row.date_sold))]
                transactions.loc[index,'status']='delete'
                a = transactions['stock']==row.stock
                b = transactions['status']=='delete'
                c = transactions[a & b].last_price
                d = transactions[a & b].quantity
                cs['value']+=(c*d).iloc[0]
                transactions = transactions[transactions['status'] !='delete']

    # Calculate the current value of each stock
    transactions['value'] = transactions['last_price']*transactions['quantity']

    # Get a subsect of transactions that were bought before current date
    transactions = transactions.append(cs)
    transactions = transactions[transactions['date_bought']<=float(str(single_date))]
    transactions['net'] = -(transactions['cost']-transactions['value'])
    transactions['net_change'] = 100*transactions['net']/transactions['cost']
    transactions = transactions[['stock','date_bought','date_sold','price','quantity','cost',
                                 'status','last_price','value','net','net_change']]
    portfolio = transactions
    
    # Calculate net value of portfolio
    net = transactions.value.sum()
    
    if (flag=='snapshot'):
        return portfolio
    
    if (flag=='returns'):
        return pd.DataFrame({'date':[single_date],'total':[net]})
        

# This is the code to call pf_stats function for a period 
        
start_date = parser.parse(str(min_date))
end_date = parser.parse(today)

net = pd.DataFrame([])

for single_date in daterange(start_date, end_date, step=1):
    if (single_date>=min_date):
        single_date=single_date.strftime("%Y%m%d")
        net = net.append(pf_stats(single_date,transactions,min_date,'returns'))

if len(net):
    net=net.set_index('date')
else:
    print "No data returned"
    

# Get data for S%P 500 from Google Finance
sp=DataReader('^GSPC', "yahoo", str(transactions.date_bought.min()),today)

# Combine SPY returns with portfolio returns
final = pd.merge(sp,net,how='inner',left_index=True,right_index=True)

# Calculate percentage change
final['sp_returns']=final.Close.pct_change()*100
final['pt_returns']=final.total.pct_change()*100

# Plot the graph to compare SPY returns with my portfolio returns
fig = plt.figure()
plt.plot_date(final.index,final.cumsum()[['sp_returns','pt_returns']],fmt='')
fig.suptitle('Portfolio vs S&P 500', fontsize=16)
plt.ylabel('percent returns',fontsize=12)
plt.xlabel('date',fontsize=12)
plt.legend(['S&P 500','Portfolio'])
plt.grid()


# Plot the graph to show net cumulative returns per security
net_summary = pf_stats('20160219',transactions,min_date,'snapshot')
net_summary = net_summary[net_summary['stock']!='cash']
net_summary = net_summary.groupby(['stock']).sum()
net_summary['net_change'] = 100*net_summary['net']/net_summary['cost']

# Define a new column to determine whether net_change is positive or negative
# This value will be used for determinning color of the bars (green if positive, red if negative)
net_summary['positive'] = net_summary['net_change'] > 0

net_summary.net_change.plot(kind='bar',
                            title='Total percentage change for each security as of day',
                            color=net_summary.positive.map({True: 'g', False: 'r'}))