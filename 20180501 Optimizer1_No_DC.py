
# coding: utf-8

# In[ ]:


from gurobipy import *
import pandas as pd

#test_data = 'D:\\USA\\SCMb\\Project\\Python\\Data_Python.xlsx'
test_data = 'Data_Python.xlsx'

block_demand = pd.read_excel(test_data, sheetname='Blockwise demand').sort_values('Block Name')
city_block = pd.read_excel(test_data, sheetname='City-Block dist in KM and min').sort_values(['Name of city', 'Name of Block'])

blocks = block_demand['Block Name'].values.tolist()
nBlock = len(blocks)
d = block_demand['Demand (no. of meals)'].values.tolist()
cities = sorted(list(set(city_block['Name of city'].values.tolist())))
nCity = len(cities)

t_city_block = []
d_city_block = []

for city, group in city_block.groupby('Name of city', sort=True):
    df = pd.DataFrame(group).sort_values('Name of Block')
    d_city_block.append(df['Distance (KM)'].values.tolist())
    t_city_block.append(df['Time needed (minutes)'].values.tolist())


model = Model()

s_k = 300000. #TR kitchen capacity
s_t = 900. #TR small truck capacity
M = 999999. # not sure
t_max = 4. * 60.
fc_k = 150000. # not sure
c_s = 0.195 # not sure
penalty=10000000

x = {}
w = {}
a = {}
u = {}

for i in range(nCity):
    x[i] = model.addVar(vtype=GRB.BINARY, name='X_' + cities[i])

for i in range(nCity):
    for k in range(nBlock):
        w[(i, k)] = model.addVar(vtype=GRB.BINARY, name='Z_' + cities[i] + '_' + blocks[k])

for i in range(nCity):
    for k in range(nBlock):
        a[(i, k)] = model.addVar(lb=0, vtype=GRB.INTEGER, name='A_' + cities[i] + '_' + blocks[k])
        
for k in range(nBlock):
    u[k] = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name='u_' + blocks[k])

model.update()

for i in range(nCity):
    for k in range(nBlock):
        model.addConstr(w[(i, k)] <= x[i], name='kitchen_open_flow_outbound_'+str(cities[i]))
        model.addConstr(a[(i, k)] <= M * w[(i, k)], name='Kitchen_flow_binding_'+str(cities[i])+'_'+str(blocks[k]))
        
for k in range(nBlock):
        model.addConstr(sum(900. * a[(i, k)] for i in range(nCity)) + u[k] >= d[k], name='Demand_'+str(blocks[k]))

for i in range(nCity):
        model.addConstr(sum(a[(i, k)] for k in range(nBlock)) <= s_k / s_t, name='Production_cap_'+str(cities[i]))

for i in range(nCity):
    for k in range(nBlock):
        model.addConstr(w[(i, k)] * t_city_block[i][k] <= t_max, name='Time_'+str(cities[i])+'_'+str(blocks[k]))
            

#TR COMMENT
# model.setObjective(
# Kitchen Fixed Cost: sum(x[i] * fc_k for i in range(nCity))
# Transport Cost:     + sum(sum(a[(i, k)] * d_city_block[i][k] * c_s for k in range(nBlock)) for i in range(nCity))
# Unmet demand:       + sum(penalty*u[k] for k in range(nBlock)),
#                 GRB.MINIMIZE)

# TR NOTE - I think this needs to be round trip transportation cost


model.setObjective(sum(x[i] * fc_k for i in range(nCity))
                 + sum(sum(a[(i, k)] * d_city_block[i][k] * c_s for k in range(nBlock)) for i in range(nCity))
                 + sum(penalty*u[k] for k in range(nBlock)),
                 GRB.MINIMIZE)

model.write('t1.lp')
model.write('t1.mps')

model.setParam('MIPGap',0.0005)
model.setParam('NodeLimit',2000)

model.optimize()


print('Objective value:', round(model.getAttr('ObjVal')))
print('Number of kitchens opened:', round(sum(x[i].getAttr('x') for i in range(nCity))))

print('Kitchen locations and number of truck deliveries:')
for i in range(nCity):
    if x[i].getAttr('x') == 1:
        print(cities[i], round(sum(a[(i, k)].getAttr('x') for k in range(nBlock))))
    
print('Total deficit: ', round(sum(u[k].getAttr('x') for k in range(nBlock))))

print('Deficit for each block:')
for k in range(nBlock):
    if u[k].getAttr('x') > 0:
        print(blocks[k], round(u[k].getAttr('x')))

print('Total cost of opening kitchens:', round(sum(x[i].getAttr('x') * fc_k for i in range(nCity))))
print('Transport cost from Kitchens to blocks:', round(sum(sum(a[(i, k)].getAttr('x') * d_city_block[i][k] * c_s for k in range(nBlock)) for i in range(nCity))))

