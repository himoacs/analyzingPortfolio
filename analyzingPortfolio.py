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

# Get today's date
today = dt.datetime.today().strftime("%Y%m%d")

# Get the transactions from csv
transactions=pd.read_csv('/Users/himanshugupta/Documents/transactions.csv')

# Get minimum transaction date
min_date = parser.parse(str(transactions.date.min()))
    
# Function for getting list of dates
def daterange(start_date, end_date, step):
    for n in range(0,int((end_date - start_date).days),step):
        yield start_date + dt.timedelta(n)




def pf_stats(single_date,transactions,min_date,flag):
    
    # Get the transactions from csv
    transactions=pd.read_csv('/Users/himanshugupta/Documents/transactions.csv')
    
    # Calculate cost of each transaction
    transactions['cost']=transactions['price']*transactions['quantity']
    
    # Defining a new dataframe which will manage our cash
    # And setting the value, cost and price of the cash to be same
    cs = transactions[transactions['stock']=='cash']
    cs['value'] = cs['cost'] = cs['price']

    # Removing cash from our transaction dataframe
    # We will add cash back in the end
    transactions = transactions[transactions['stock']!='cash']
    
    # Only looking at transactions which happened today or prior to today
    # so we can ignore future transactions
    transactions = transactions[transactions['date']<=float(str(single_date))]

    # Get a list of unique stocks in your portfolio
    unique_stocks = pd.unique(transactions.stock)
        
    # Get prices from Google Finance for each unique stock
    price={}
    for ticker in unique_stocks:
        price[ticker] = DataReader(ticker,"yahoo",str(min_date),single_date)
    
    # Loop through the transactions
    # For each buy:
    # 1. update the 'value' of the security using the latest adjusted close price
    # 2. take the price you bought the security at and multiply with the quantity
    #    to get the cost of security and subtract it from cash
    # For each sell:
    # 1. update the 'value' of the security using transaction price * quantity
    # 2. subtract the value calculated above and add it to cash
    for index,row in transactions.iterrows():

        if (row.trans=='buy'):
            transactions.loc[index,'value']=row.quantity*price[row.stock].tail(n=1)['Adj Close'].ix[0]
            cs['value']=(cs['value']-(row.price*row.quantity))
        if (row.trans=='sell'):
            transactions.loc[index,'value']=row.quantity*row.price
            cs['value']=(cs['value']+(row.price*row.quantity))
    
    # Create a new dataframe called 'transactions_active' by grouping 'transactions' dataframe
    # by 'stock' and 'trans' and then sum everything up
    # This is so that if there are multiple transactions for same security, they will all be
    # grouped into one for 'buy' and one for 'sell'.
    transactions_active = transactions.groupby(['stock','trans']).sum()
    transactions_active = transactions_active.reset_index()
    transactions_active = transactions_active[['stock','trans','quantity','cost','value']]

    # For each transaction in 'transactions_active':
    # 1. look at the 'sell' row and get these three values:
    #       i) new_quantity: number of shares left after selling
    #       ii) new_value: value of the number of shares left
    #       iii) new_cost: money it cost you to buy these remaining shares
    #                 a) this value is calculated by using the average method
    # Once these values are calculated, update the corresponding quantity,cost and value
    # cells for the 'buy' transaction. Leave the 'sell' transaction as it is, we will 
    # get rid of it later.
    for index,row in transactions_active.iterrows():

        if (row.trans=='sell'):

            a = transactions_active['stock']==row.stock
            b = transactions_active['trans']=='buy'

            new_quantity = (transactions_active[a & b].quantity.iloc[0])-(row.quantity)
            new_value = new_quantity*(price[row.stock].tail(n=1)['Adj Close'].ix[0])
            new_cost = (transactions_active[a & b].cost/transactions_active[a & b].quantity)*new_quantity

            transactions_active[a & b] = transactions_active[a & b].set_value(
                                            transactions_active[a & b].index,'value',new_value)
            transactions_active[a & b] = transactions_active[a & b].set_value(
                                            transactions_active[a & b].index,'quantity',new_quantity)
            transactions_active[a & b] = transactions_active[a & b].set_value(
                                            transactions_active[a & b].index,'cost',new_cost)
    
    # Remove 'sell' transactions
    transactions_active = transactions_active[transactions_active['trans']!='sell']
    
    # Add cash to transactions dataframe
    transactions_active = transactions_active.append(cs)
    
    # Calculate 'net' by taking 'value' and subtracting 'cost from it
    transactions_active['net'] = (transactions_active['value']-transactions_active['cost'])
    
    # Calculate 'net_change'
    transactions_active['net_change'] = 100*transactions_active['net']/transactions_active['cost']
    
    # Calculate net value of entire portfolio
    net = transactions_active.value.sum() 

    # If flag is set to 'snapshot' then return entire dataframe
    # If flag is set to 'returns' then only return the net value of portfolio
    if (flag=='snapshot'):
        return transactions_active

    if (flag=='returns'):
        return pd.DataFrame({'date':[single_date],'total':[net]})    
        



### Calling the Function ###

start_date = parser.parse('20160105')
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
sp=DataReader('^GSPC', "yahoo", str(transactions.date.min()),today)

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

# Get snapshot of our portfolio for a specific date
net_summary = pf_stats('20160325',transactions,min_date,'snapshot')

# Remove cash from portfolio
net_summary = net_summary[net_summary['stock']!='cash']

# Only include securities we currently hold (i.e. quantity>0)
net_summary = net_summary[net_summary.quantity>0]

# Sum the data by 'stock' and calculate 'net_change'
net_summary = net_summary.groupby(['stock']).sum()
net_summary['net_change'] = 100*net_summary['net']/net_summary['cost']

# Define a new column to determine whether net_change is positive or negative
# This value will be used for determinning color of the bars (green if positive, red if negative)
net_summary['positive'] = net_summary['net_change'] > 0

net_summary.net_change.plot(kind='bar',
                            title='Total percentage change for each security as of day',
                            color=net_summary.positive.map({True: 'g', False: 'r'}))
                            
