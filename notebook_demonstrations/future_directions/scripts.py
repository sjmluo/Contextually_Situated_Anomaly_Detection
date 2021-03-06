'''
AUTHORS: TONY WANG, YEE CHIN
FOR ANOMALY DETECTION PROJECT, USYD, SIMON LUO, PRASAD CHEEMA
scripts.py contains the data processing and other useful generic functions 
for the contextual anomaly detection project.
'''

import pandas as pd 
import numpy as np 
from scipy.signal import welch
import stumpy
from stumpy.floss import _cac
from vmdpy import VMD
import ot 
import matplotlib.pyplot as plt
from matplotlib import animation 
from IPython.display import HTML 


def exp_list_process(data_dict, cases, num_healthy):
    '''
    Input: data_dict::dict, cases::list, num_healthy::int
    Given a dictionary data_dict of the form {Sensorn : data} and
    a list of cases of the form [location, damage_level, voltage_level] (e.g. ['L00','D00','V08']), 
    return a dictionary df_list of the form {Sensorn : data} with exactly num_healthy cases
    and 5 of each other case outlined in cases.
    '''
    num_sensors = len(data_dict.keys())
    df_list = dict()

    for sensor_num in range(1,num_sensors+1):
        sensor_str = 'Sensor'+str(sensor_num)
        df = data_dict[sensor_str]
        df_list_temp = []
        for num in cases:
            query1 = (df['damage_location']==num[0]).values
            query2 = (df['damage_level']==num[1]).values
            query3 = (df['voltage_level']==num[2]).values

            df_query = df[query1 & query2 & query3]
            df_list_temp.append(df_query.reset_index(drop=True)) # Organize cases per sensor
            
        df_list[sensor_str] = pd.concat(df_list_temp) # Concatenate cases across each sensor
        
        # Removing 50 num_healthy D00 (heahlthy i.e. non damage) cases 
        # Because a lot of the damage case only have 5 events recorded in total
        # We shall have 50-num_healthy D00 --> 5 DB0 --> 5 DBB --> 5 DBB cases in a sequence
        df_list[sensor_str] =  df_list[sensor_str].iloc[50-num_healthy:,:].reset_index(drop=True)
    
    return df_list 

def welch_vmd(df_list, signal_length=8192, nperseg=1024, fs=1600, vmd=0, alpha=0, tau=0, DC=0, init=0, tol=0):
    '''
    Input: 
    df_list::dict, signal_length::int, nperseg::int, fs::int, vmd::int, alpha::int, tau::int, DC:;int, init::int, tol::int.
    df_list should be a dict {Sensorn : data}.
    If vmd > 0, perform variational mode decomposition with num_modes = vmd and all other parameters specified (we use the default parameters).
    If vmd = 0, do not perform vmd.
    Output: 
    A dictionary building_features of the form {Sensorn : {experimentk : (vmdj)}}, a stacked dictionary 
    containing tuples of vmd modes.
    
    In terms of the data pipeline, this should be placed after the correct experimental data has been pulled out of Building_Model.mat into df_list. Just iterate over the number of sensors. 
    This gives us flexibility in case we want to experiment with different combinations of normal/anomalous data etc. 
    '''  

    
    if vmd >= 1: 
        first_item = next(iter(df_list.values()))
        num_experiments = len(first_item)

        num_sensors = len(df_list.keys())
        building_features = dict()
        for sensor_num in range(1,num_sensors+1):
            # For Each Sensor
            sensor_str = f'Sensor{sensor_num}'
            sensor_values = df_list[sensor_str].iloc[:,:signal_length].values
            print(f'Processing Sensor {sensor_num}')
            building_features[sensor_str] = dict() # Initialize nested dictionary (sensor_num : experiment_num : values)

            # For Each Experiment
            for i in range(num_experiments):
                experiment_str = f'Experiment{i+1}'
                data_row = sensor_values[i,:]
                data_row_demeaned = data_row - np.mean(data_row) # Remove "DC" component (i.e. de-mean)
                u, _, _ = VMD(data_row_demeaned, alpha, tau, vmd, DC, init, tol)  # Return K x n-array from n-array input
                if i%5 == 0:
                    print(f'\tProcessed VMD for Experiment Num (i.e. Data Row) {i}')

                vmd_list = []
                for j in range(vmd):
                    # For Each VMD Signal More Feature Engineering
                    # Paper for welch: http://bobweigel.net/csi763/images/Welch_1967.pdf
                    pxx = welch(u[j,:], fs=fs, nperseg=nperseg) # Returns len 2 tuple
                    vmd_list.append(np.log(pxx[1]/max(pxx[1]))) # Feature Engineering
                
                building_features[sensor_str][experiment_str] = np.array(vmd_list)
        return building_features
    
    if vmd == 0: 
        # if df_list contains other things, take the length of the appropriate data
        df_list = df_list.iloc[:,:8192]

        building_features = dict()
        welch_list = []

        num_experiments = len(df_list)

        for i in range(num_experiments):
            experiment_str = f'Experiment{i+1}'
            data_row = df_list.iloc[i,:8192]
            data_row_demeaned = data_row - np.mean(data_row) # Remove "DC" component (i.e. de-mean)
            
            pxx = welch(data_row_demeaned, fs=1600, nperseg=nperseg) # Returns len 2 tuple
            welch_list.append(np.log(pxx[1]/max(pxx[1]))) # Feature Engineering
            
            building_features[experiment_str] = np.array(welch_list)

            welch_list.clear()
        return building_features


def data_sequencing(building_features, vmd):
    '''
    Input: building_features::dict, vmd::int
    Given a dictionary building_features of the form {Sensorn : {vmd : data}} (if vmd != 0) or 
    {Sensorn : data} (if vmd = 0), concatenate together the transformed data for each experiment for each VMD mode and sensor. 
    Returns a dictionary building_features_seq of the form {Sensorn : (vmdk_concat)}.
    '''
    if vmd >= 1:
        num_sensors= len(building_features.keys())
        num_experiments = len(building_features['Sensor1'].keys())

        building_features_seq = dict()
        for i in range(1,num_sensors+1):
            sensor_str = f'Sensor{i}'
            
            stack_list = []
            for j in range(1,num_experiments+1):
                experiment_str = f'Experiment{j}'
                stack_list.append(building_features[sensor_str][experiment_str])
                
            building_features_seq[sensor_str] = np.hstack(stack_list)
        return building_features_seq 

    if vmd == 0: 
        num_experiments = len(building_features.keys())
        return np.hstack([building_features[f'Experiment{i+1}'] for i in range(num_experiments)]).squeeze()
        

def animate_regime_change(building_seq, filename, num_modes, regime_change_idxs, start_list_size, m, L):
    '''
    Input: building_seq::dict, filename::str, num_modes::int, regime_change_idxs::list, start_list_size::int, m::int, L::int
    building_seq should be of the form {Sensorn : (vmdk_concat)} (returned dictionary from data_sequencing).
    This function will automatically save a gif with the name filename. 
    num_modes should be the number of vmd modes used.
    regime_change_idxs should be the indices of the theoretical regime changes: for example, [10*513, 15*513, 20*513].
    start_list_size was originally 513*5 and denotes the size of the initial data.
    m and L are generally set to be equal, with m = L = 100.

    Output: a gif animating the CAC being updated as sensor data comes in.
    Note: this currently only works for building_seq where building_seq is only of 1 sensor. For multiple sensors, 
    '''
    if num_modes > 0: 

        cac_list = [] #to store the initial cacs for each mode 

        stream = dict()

        #initialising and also setting up streaming objects for each mode
        for mode in range(num_modes): 
            old_data = building_seq[mode][:start_list_size] # take the first 5 experiments. There are 25 experiments, with changes occuring in 10, 15, 20 
            mp = stumpy.stump(old_data, m=m)
            cac_list.append(_cac(mp[:, 3], L, bidirectional=False, excl_factor=1))
            vmd_str = f'vmd{mode}'
            stream[vmd_str] = stumpy.floss(mp, old_data, m=m, L=L, excl_factor=1)

        cac_list= np.array(cac_list)
        #OT layer 1 for initial data ( first five experiments)
        sub_sample_rate = 10

        A = cac_list.T
        B = A[::sub_sample_rate,:] # Sub-sampling to increase OT processing
        M = ot.utils.dist0(B.shape[0]) # Ground Metric 
        M /= M.max()  # Normalizing ground metric 
        M*=1e+4 # Tuning ground metric for problem (hyper-param)

        bary_wass = ot.barycenter_unbalanced(B, M, reg=5e-4, reg_m=1e-1) # reg - Entropic Regularization 

        cac_1d = np.repeat(bary_wass,10)

        windows = []

        current_x_window = list(np.arange(start_list_size))

        new_data = building_seq.T[start_list_size:]

        for i, t in enumerate(new_data): 
            
            #update the window of x values we are currently looking at CAC for
            current_x_window = current_x_window[1:]
            current_x_window.append(i+start_list_size)

            cac_list = []

            for mode in range(num_modes):
                vmd_str = f'vmd{mode}'
                stream[vmd_str].update(t[mode])
                cac_list.append(stream[vmd_str].cac_1d_)
            cac_list = np.array(cac_list)

            if i % 100 == 0:
                #note any indices of regime changes in this x values window
                regime_changes_window_idxs = [0]
                for change in regime_change_idxs:
                    if change in current_x_window:
                        regime_changes_window_idxs.append(current_x_window.index(change))
                        
                #layer 1 pooling over modes
                sub_sample_rate = 10 #for fast OT processing
                A = cac_list.T
                B = A[::sub_sample_rate,:] # Sub-sampling to increase OT processing
                M = ot.utils.dist0(B.shape[0]) # Ground Metric 
                M /= M.max()  # Normalizing ground metric 
                M*=1e+4 # Tuning ground metric for problem (hyper-param)

                bary_wass = ot.barycenter_unbalanced(B, M, reg=5e-4, reg_m=1e-1) # reg - Entropic Regularization 

                current_cac_1d = np.repeat(bary_wass,10)
                
                windows.append((stream['vmd1'].T_, current_cac_1d, regime_changes_window_idxs))


        fig, axs = plt.subplots(2, sharex=True, gridspec_kw={'hspace': 0})

        axs[0].set_xlim((0, len(current_x_window)))
        Y_MIN = np.min(building_seq[0])
        Y_MAX = np.max(building_seq[0])
        axs[0].set_ylim(Y_MIN, Y_MAX)
        axs[1].set_xlim((0, len(current_x_window)))
        axs[1].set_ylim((-0.1, 1.1))

        lines = []

        for ax in axs: #create empty structures for each frame
            line, = ax.plot([], [], lw=2)
            lines.append(line)
            line, = ax.plot([],[], linewidth=2, color= 'red')
            lines.append(line)
        line, = axs[1].plot([], [], lw=2) # create structure for orange curve
        lines.append(line)

        def init():
            for line in lines:
                line.set_data([], [])
            return lines

        def animate(window):
            data_out, cac_out, regime_changes = window
            lines[0].set_data(np.arange(data_out.shape[0]), data_out)
            lines[2].set_data(np.arange(cac_out.shape[0]), cac_out)
            rgm_change = max(regime_changes)
            lines[1].set_data([rgm_change,rgm_change],[Y_MIN, Y_MAX])
            lines[3].set_data([rgm_change,rgm_change],[-0.1, 1.1])
            return lines

        anim = animation.FuncAnimation(fig, animate, init_func=init,
                                    frames=windows, interval=100,
                                    blit=True)

        writergif = animation.PillowWriter(fps = 10)
        anim.save(filename,writer=writergif)

        anim_out = anim.to_jshtml()
        plt.close()  # Prevents duplicate image from displaying

        
        return HTML(anim_out)

    else:  ### mode == 0
        old_data = building_seq[:start_list_size]
        new_data = building_seq[start_list_size:] # take the first 5 experiments. There are 25 experiments, with changes occuring in 10, 15, 20 
        mp = stumpy.stump(old_data, m=m)
        cac_1d = _cac(mp[:, 3], L, bidirectional=False, excl_factor=1)  # This is for demo purposes only. Use floss() below!
        stream = stumpy.floss(mp, old_data, m=m, L=L, excl_factor=1)

        old_data = building_seq[:513*5]
        new_data = building_seq[513*5:] # take the first 5 experiments. There are 25 experiments, with changes occuring in 10, 15, 20 
        mp = stumpy.stump(old_data, m=m)
        cac_1d = _cac(mp[:, 3], L, bidirectional=False, excl_factor=1)  # This is for demo purposes only. Use floss() below!
        stream = stumpy.floss(mp, old_data, m=m, L=L, excl_factor=1)

        windows = []

        regime_change_idxs = []
        for n_exp in [10,15,20]:
            regime_change_idxs.append(n_exp*513)

        current_x_window = list(np.arange(513*5))

        for i, t in enumerate(new_data): 
            stream.update(t)
            
            #update the window of x values we are currently looking at CAC for
            current_x_window = current_x_window[1:]
            current_x_window.append(i+513*5)
            
            if i % 100 == 0:
                #note any indices of regime changes in this x values window
                regime_changes_window_idxs = [0]
                for change in regime_change_idxs:
                    if change in current_x_window:
                        regime_changes_window_idxs.append(current_x_window.index(change))
                windows.append((stream.T_, stream.cac_1d_, regime_changes_window_idxs))
                # window contains tuples of the form (time_series, cac, regime_changes_window_idxs)
                


        fig, axs = plt.subplots(2, sharex=True, gridspec_kw={'hspace': 0})

        axs[0].set_xlim((0, mp.shape[0]))
        Y_MIN = min(np.min(old_data), np.min(new_data))
        Y_MAX = max(np.max(old_data), np.max(new_data))
        axs[0].set_ylim(Y_MIN, Y_MAX)
        axs[1].set_xlim((0, mp.shape[0]))
        axs[1].set_ylim((-0.1, 1.1))

        #legend here^ try

        lines = []

        for ax in axs: #create empty structures for each frame
            line, = ax.plot([], [], lw=2)
            lines.append(line)
            line, = ax.plot([],[], linewidth=2, color= 'red')
            lines.append(line)
        line, = axs[1].plot([], [], lw=2) # create structure for orange curve
        lines.append(line)

        def init():
            for line in lines:
                line.set_data([], [])
            return lines

        def animate(window):
            data_out, cac_out, regime_changes = window
        #     for line, data in zip(lines, [data_out, regime_changes, cac_out, regime_changes, cac_1d]):
        #         line.set_data(np.arange(data.shape[0]), data)
            lines[0].set_data(np.arange(data_out.shape[0]), data_out)
            lines[2].set_data(np.arange(cac_out.shape[0]), cac_out)
        #     lines[4].set_data(np.arange(cac_1d.shape[0]), cac_1d)
            rgm_change = max(regime_changes)
            lines[1].set_data([rgm_change,rgm_change],[Y_MIN, Y_MAX])
            lines[3].set_data([rgm_change,rgm_change],[-0.1, 1.1])
            return lines

        anim = animation.FuncAnimation(fig, animate, init_func=init,
                                    frames=windows, interval=100,
                                    blit=True)

        writergif = animation.PillowWriter(fps = 10)
        anim.save(filename,writer=writergif)

        anim_out = anim.to_jshtml()
        plt.close()  # Prevents duplicate image from displaying

        return HTML(anim_out)

def compute_bary_cacs(building_features_seq, subsample_rate, num_sensors, num_modes):
    '''
    Input: building_features_seq::dict, subsample_rate::int, num_sensors::int, num_modes
    Given input building_features_seq of the form dict: {sensor_num: (vmd1, ..., vmd_num_modes)}, 
    compute the output
    Output: A dict of the form {sensor_num: cac}, 
    where cac is the cacs of the vmds barycentered together.
    '''
    cac_dict = dict()
    for i in range(num_sensors):
        bary_cac = []
        sensor_str = f'Sensor{i+1}'
        for j in range(num_modes):
            bary_cac.append(building_features_seq[sensor_str][j])
        bary_cac = np.array(bary_cac)

        A = bary_cac.T
        B = A[::subsample_rate, :]
        M = ot.utils.dist0(B.shape[0])
        M /= M.max()
        M*=1e4

        bary_wass = ot.barycenter_unbalanced(B, M, reg=5e-4, reg_m=1e-1)
        cac_dict[sensor_str] = bary_wass
    return cac_dict


def final_cac(building_cacs, num_sensors, subsample_rate, average):
    '''
    Given a dict {sensor_num: cac}, either barycenter the cacs together or average. 
    Return an array of cac values. 
    Give a subsample rate of 1 if compute_bary_cacs was used.
    '''
    if average == True: 
        # compute averages of cacs 
        AVG = []
        for i in range(num_sensors):
            sensor_str = f'Sensor{i+1}'
            AVG.append(building_cacs[sensor_str])
        final_AVG = np.array(AVG).mean(axis=0)

        return final_AVG

    else: 
    # cac together 
        OT = []
        for i in range(num_sensors):
            sensor_str = f'Sensor{i+1}'
            OT.append(building_cacs[sensor_str])
        OT = np.array(OT)
        
        A = OT.T
        B = A[::subsample_rate, :]
        M = ot.utils.dist0(B.shape[0])
        M /= M.max()
        M*=1e4

        final_OT = ot.barycenter_unbalanced(B, M, reg=2e-4, reg_m=9e-4)

        return final_OT

def zero_out(data, length_zero, length_data, num_experiments, zero=True, rand=True):
    '''
    Given a pandas dataframe data (e.g. data_dict['Sensor1']), 
    return a dataframe with random segments either zeroed out (zero==true) or
    replaced by a random normal segment horizontally (along the columns).
    if random==True, provide a random integer length to be zeroed out.
    num_experiments: number of experiments to zero out in each dataframe
    length_zero = (a,b) (if rand=True) or an integer if anything else 
    length_data = 8192
    Chooses random position and a random length of data determined by length_zero to zero out.
    '''
    rand_positions = []
    if rand == True: 
        a, b = length_zero
        return_len = np.random.randint(a,b)
    else: 
        return_len = length_zero 

    for i in range(num_experiments):
        rand_pos = np.random.randint(0, length_data - return_len)
        if zero == True:
            data.iloc[i,rand_pos:rand_pos+return_len] = 0
        else: 
            data.iloc[i,rand_pos:rand_pos+return_len] = np.random.normal(loc=0, scale=1, size=return_len)
        rand_positions.append(rand_pos)

    return data, rand_positions


def temporal_shift(data, length_shift, length_data, num_experiments):
    '''Given a pandas dataframe data (e.g. data_dict['Sensor1']), 
    return a dataframe with experiments shifted by :int shift. 
    If shift is a 2-tuple (a,b), randomly choose a value in [a,b] to shift each experiment 
    '''
    shifts = []
    for i in range(num_experiments):
        if type(length_shift) == tuple: 
            shift_val = np.random.randint(length_shift[0], length_shift[1])
        else:
            shift_val = length_shift
        shifts.append(shift_val)
        data.iloc[i,shift_val:length_data] = data.iloc[i,:length_data-shift_val]
        data.iloc[i,:shift_val] = 0 
    return data, shifts

def multisensor(func, sensors, args):
    '''
    Inputs: func::function, sensors::list
    Apply func to a subset of data determined by sensors (a list of integers between 1 and max_sensors). The arguments for the function should be 
    provided in a tuple or list in args.
    '''
    data, length_effect, length_data, num_experiments = args

    for sens in sensors: 
        sensor_str = f'Sensor{sens}'
        func(data[sensor_str], length_effect, length_data, num_experiments)