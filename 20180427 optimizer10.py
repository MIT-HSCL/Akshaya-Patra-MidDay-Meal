from gurobipy import *
import pandas as pd

#test_data = 'D:\\USA\\SCMb\\Project\\Python\\Data_Python.xlsx'
test_data = 'Data_Python_2.xlsx'

block_demand = pd.read_excel(test_data, sheetname='Blockwise demand').sort_values('Block Name')
city_block = pd.read_excel(test_data, sheetname='City-Block dist in KM and min').sort_values(['Name of city', 'Name of Block'])
city_city = pd.read_excel(test_data, sheetname='City-city dist in KM and min').sort_values(['From', 'To'])

blocks = block_demand['Block Name'].values.tolist()
nBlock = len(blocks)
d = block_demand['Demand (no. of meals)'].values.tolist()
cities = sorted(list(set(city_city['From'].values.tolist())))
nCity = len(cities)

t_city_city = []
d_city_city = []

for city, group in city_city.groupby('From', sort=True):
    df = pd.DataFrame(group).sort_values('To')
    d_city_city.append(df['Distance (KM)'].values.tolist())
    t_city_city.append(df['Time needed (minutes)'].values.tolist())


t_city_block = []
d_city_block = []

for city, group in city_block.groupby('Name of city', sort=True):
    df = pd.DataFrame(group).sort_values('Name of Block')
    d_city_block.append(df['Distance (KM)'].values.tolist())
    t_city_block.append(df['Time needed (minutes)'].values.tolist())


model = Model()

s_k = 300000.
s_t = 9000.
M = 99999999999. # not sure
t_cd = 30.
t_max = 6. * 60.
fc_k = 150000. # not sure
fc_dc = 1.
c_b = 0.3 # not sure
c_s = 0.195 # not sure
penalty=10000000

x = {}
y = {}
w = {}
z = {}
a = {}
b = {}
u = {}

for i in range(nCity):
    x[i] = model.addVar(vtype=GRB.BINARY, name='X_' + cities[i])

for j in range(nCity):
    y[j] = model.addVar(vtype=GRB.BINARY, name='Y_' + cities[j])

##Francisco Change
for i in range(nCity):
    for j in range(nCity):
#        w[(i, j)] = model.addVar(vtype=GRB.BINARY, name='W_' + cities[i] + '_' + cities[j])
        w[(i, j)] = model.addVar(vtype=GRB.CONTINUOUS, name='W_' + cities[i] + '_' + cities[j])
    
##Francisco Change    
for j in range(nCity):
    for k in range(nBlock):
#        z[(j, k)] = model.addVar(vtype=GRB.BINARY, name='Z_' + cities[j] + '_' + blocks[k])
        z[(j, k)] = model.addVar(vtype=GRB.CONTINUOUS, name='Z_' + cities[j] + '_' + blocks[k])

##Francisco Change 
for i in range(nCity):
    for j in range(nCity):
 #       a[(i, j)] = model.addVar(lb=0, vtype=GRB.INTEGER, name='a_' + cities[i] + '_' + cities[j])
         a[(i, j)] = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name='a_' + cities[i] + '_' + cities[j])

for j in range(nCity):
    for k in range(nBlock):
#        b[(j, k)] = model.addVar(lb=0, vtype=GRB.INTEGER, name='b_' + cities[j] + '_' + blocks[k])
        b[(j, k)] = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name='b_' + cities[j] + '_' + blocks[k])
        
for k in range(nBlock):
    u[k] = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name='u_' + blocks[k])

model.update()

for i in range(nCity):
    for j in range(nCity):
        model.addConstr(w[(i, j)] <= x[i], name='Kitchen_open_flow_outbound_'+str(cities[i]))
        model.addConstr(w[(i, j)] <= y[j], name='DC_open_flow_inbound_'+str(cities[j]))

for j in range(nCity):
    for k in range(nBlock):
        model.addConstr(z[(j, k)] <= y[j], name='DC_open_flow_outbound_'+str(cities[j]))
        model.addConstr(b[(j, k)] <= M * z[(j, k)], name='DC_flow_binding_'+str(cities[j])+'_'+str(blocks[k]))
        
for k in range(nBlock):
        model.addConstr(sum(900.*b[(j, k)] for j in range(nCity)) + u[k] >= d[k], name='Demand_'+str(blocks[k]))

for i in range(nCity):
    for j in range(nCity):
        model.addConstr(a[(i, j)] <= s_k / s_t, name='Production_'+str(cities[i]))
        model.addConstr(a[(i, j)] <= M * w[(i, j)], name='kitchen_flow_binding_'+str(cities[i]))

for i in range(nCity):
    for j in range(nCity):
        for k in range(nBlock):
            model.addConstr(w[(i, j)] * t_city_city[i][j] + z[(j, k)] * t_city_block[j][k] + t_cd <= t_max, name='Time_'+str(cities[i])+'_'+str(blocks[k]))
            
for j in range(nCity):
    model.addConstr(sum(a[(i, j)] * 9000. for i in range(nCity)) == sum(b[(j, k)] * 900. for k in range(nBlock)), name='Flow_conservation_'+str(cities[j]))

for i in range(nCity):
    model.addConstr(x[i] <= y[i], name='Co_location_'+str(cities[i]))

model.setObjective(sum(x[i] * fc_k for i in range(nCity))
                 + sum(y[j] * fc_dc for j in range(nCity))
                 + sum(sum(a[(i, j)] * d_city_city[i][j] * c_b for j in range(nCity)) for i in range(nCity))
                 + sum(sum(b[(j, k)] * d_city_block[j][k] * c_s for k in range(nBlock)) for j in range(nCity))
                 + sum(penalty*u[k] for k in range(nBlock)),
                 GRB.MINIMIZE)

model.write('t1.lp')
model.write('t1.mps')

model.setParam('MIPGap',0.0005)
model.setParam('NodeLimit',2000)
model.setParam('Cuts',1)
model.setParam('CutPasses',30)
model.setParam('BranchDir',-1)

model.optimize()


print('Objective value:', round(model.getAttr('ObjVal')))
print('Number of kitchens opened:', round(sum(x[i].getAttr('x') for i in range(nCity))))
print('Number of DCs opened:', round(sum(y[j].getAttr('x') for j in range(nCity))))

print('Kitchen locations and number of truck deliveries:')
for i in range(nCity):
    if x[i].getAttr('x') == 1:
        print(cities[i], round(sum(a[(i, j)].getAttr('x') for j in range(nCity))))

print('DC locations and number of truck deliveries:')
for j in range(nCity):
    if y[j].getAttr('x') == 1:
        print(cities[j], round(sum(b[(j, k)].getAttr('x') for k in range(nBlock))))
    
print('Total deficit: ', round(sum(u[k].getAttr('x') for k in range(nBlock))))

print('Deficit for each block:')
for k in range(nBlock):
    if u[k].getAttr('x') > 0:
        print(blocks[k], round(u[k].getAttr('x')))

print('Total cost of opening kitchens:', round(sum(x[i].getAttr('x') * fc_k for i in range(nCity))))
print('Total cost of opening DCs:', round(sum(y[j].getAttr('x') * fc_k for j in range(nCity))))
print('Transport cost from kitchens to DCs:', round(sum(sum(a[(i, j)].getAttr('x') * d_city_city[i][j] * c_b for j in range(nCity)) for i in range(nCity))))
print('Transport cost from DCs to blocks:', round(sum(sum(b[(j, k)].getAttr('x') * d_city_block[j][k] * c_s for k in range(nBlock)) for j in range(nCity))))
