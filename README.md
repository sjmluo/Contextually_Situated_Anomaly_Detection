<h1 align="center">
  <b>Contextually Situated Anomaly Detection</b><br>
</h1>

<p align="center">
      <a href="https://www.python.org/">
        <img src="https://img.shields.io/badge/Python-3.7-ff69b4.svg" /></a>    
</p>

Given (time-series) data from multiple sensors and a structure that is experiencing changing states (e.g. progressively increasing damage in certain parts of the structure), is it possible to segment the data to detect when such transitions occur? 

In this repository, we present code and demonstrations of our proposed methodology for solving this class of problems, based on the matrix profile data structure and the fast semantic segmentation algorithm. We focus on problems in engineering contexts: in particular, we look at arrays of accelerometer data on the following structures - a three storeyed building, a plane and a bridge, involving complex and noisy data that is not easy to work with with generic statistical or machine learning techniques.

Our methods build on a special data structure called the matrix profile which computes the pairwise maximal distances between subsequences of a given window length. The matrix profile provides a list of "nearest neighbour indices", which is important for _semantic segmentation_. Each nearest neighbour index defines an "arc" (like an arrow) from one data point to another, and for each data point, we can count the number of times an arc crosses above the point.   

<p float="none">
  <img src="image_assets/arc_curve_pointer_ex.png?raw=true "Title"" width="400" />
</p>

When the statistical properties of the generating random process changes significantly over a period of time, the number of arcs crossing over points in and around the transition decreases significantly. After dividing by a correction factor (in the baseline random-neighbours scenario, we expect more crossovers for data points in the center than data points on the extremities), we obtain the _Corrected Arc Curve_ (CAC), which "reacts" numerically to perceived regime changes.

<p float="none">
  <img src="image_assets/noisy_cac_single.jpg?raw=true "Title"" width="400" />
</p>

 In this way, the matrix profile gives a very interpretable meaning to the anomalous transitions it detects. Contrast this with the difficult-to-interpret black-box methods popularised by neural learning, which is particularly inapplicable to high-risk operations (such as the ones we consider in this repository) where understanding how a model categorises failure/anomalies is almost as important as the categorisation itself! We refer to https://stumpy.readthedocs.io/en/latest/, in particular Tutorials/Semantic Segmentation, for more details on the theoretical foundations of the matrix profile.

In order to combine information from multiple sensors more effectively, we use the _Wasserstein Barycenter_ from Optimal Transport theory %insert image of combined CAC%.  Combining these tools together along with classic signal processing transformations such as the Welch transform, we have created a prototype of an end-to-end anomaly detection algorithm in both offline and online scenarios capable of accurately detecting transitions in a wide variety of contexts. 

In order to demonstrate the algorithms we use, we have created a number of Jupyter notebook demonstrations. These are contained in the notebook_demonstrations folder. These are (broadly) categorised under the following folders:
1. Baseline models. In this folder, we apply two classes of machine learning models used for classification (Feature Extraction-SVM and 1D Convolution Networks) to the damage classification problem. We use the performances from these models as benchmarks for the matrix profiling methods we will showcase, and also to contrast the benefits of an unsupervised noise-robust algorithm against classical supervised black-box models. These simple models were built in Tensorflow/Keras (Python).
2. Offline methodology. In this folder, we display an example of the end-to-end algorithm, starting with raw sensor data, applying transformations into the frequency domain and smoothing techniques, applying the Variational Mode Decomposition (VMD) and computing the matrix profile before ensembling the resulting curve together with the Wasserstein barycenter to produce a final estimate of anomalous transition positions. The resulting detector is able to demarcate all anomalous transitions with 100% accuracy.
3.  Online methodology. In this folder, we display our extensions to the offline end-to-end algorithm to work with real-time data. As data-points arrive, the matrix profiles are able to be updated in a sequential fashion with low time complexity owing to the way the matrix profile is defined. By animating the resulting curves in time as data points are added in, we can visualise how the detector reacts to increasing damage in real-time. Our results show that all anomalous transitions are detected with 100% accuracy. The animations are included in the Jupyter notebook. 
- The online methodology working on the original data can be found in notebook_demonstrations/streaming as intro_streaming_bookshelf.ipynb. To test the robustness of our online algorithm, we also apply our methods on corrupted data (a common scenario in live operational environments). These are located within sensor_errors.ipynb (sensors zeroing out random segments) and temporal_shifts.ipynb (sensor data being shifted forward in time relative to other sensors). We show that our methods remain 100% accurate, clearly demarcating regime changes even when a significant percentage of the given sensors are damaged.

## Requirements and Installation
- Python >= 3.7.12 

Have a read of requirements/readme_requirements.txt and data_readme.txt. We summarise the information here.

Download the "data" folder from https://drive.google.com/drive/folders/145TEZCV3NC5FD3FeY_GvTQaoQ6yqni2L?usp=sharing. Save it into the repository. 

For the end-to-end notebooks (offline and online), run
```
$ cd requirements
$ pip install -r end2end-requirements.txt
```
For the benchmark models, preferably in a separate virtual environment, run 
```
$ cd requirements
$ pip install -r tf_requirements.txt
```
Having multiple environments is preferred due to Tensorflow conflicts with other packages especially if you are working on ARM architecture chips (such as the Apple M1s). You can also run the setup.sh scripts located inside the relevant folders.

## Images 
The following are images of outputs from our proposed methodology. The red vertical lines denote the true locations of the regime changes. The first two images are from the offline methodology, where a batch of input data is transformed and CACs computed to predict possible anomalous transitions. The last gif is the output from our online methodology: as input data is fed in, the CAC curve updates and "reacts" to an anomalous transition by dipping. After barycentering over the data from all 24 sensors, we see a marked improvement in the smoothness of the anomaly predictor. All possible anomalous transitions are clearly demarcated by our methods.  

Note: we have plotted 1-CAC in the first two images for peak-finder algorithms. Since we do not use a peak-finder algorithm in the online methodology, we use the original CAC.
<p float="left">
  <img src="image_assets/CAC_responses.jpg?raw=true "Title"" width="700" />
  <img src="image_assets/combined_CAC_24.jpg?raw=true "Title"" width="700" />
  <img src="image_assets/welch-cac-10fps.gif?raw=true "Title"" width="700" /> 
</p>

<p float="left>
  <img src="image_assets/smoothed_CAC_anim.gif?raw=true "Title"" width="700 />
 </p>

