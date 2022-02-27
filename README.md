<h1 align="center">
  <b>Contextually Situated Anomaly Detection</b><br>
</h1>

<p align="center">
      <a href="https://www.python.org/">
        <img src="https://img.shields.io/badge/Python-3.7-ff69b4.svg" /></a>    
</p>


In this repository, we present our innovations on the matrix profile data structure to detecting anomalies in context. 

The problem we are trying to solve is the following. Given (time-series) data from multiple sensors and a structure that is experiencing changing states (e.g. progressively increasing damage in certain parts of the structure), is it possible to segment the data to detect when such transitions occur? 

To solve this problem, the main tool we use is the _matrix profile_, a data structure which computes the pairwise maximal distances between subsequences of a certain length. The matrix profile provides a list of "nearest neighbour indices", which is important for _semantic segmentation_ purposes. We refer to https://stumpy.readthedocs.io/en/latest/, in particular Tutorials/Semantic Segmentation, for more details. 

In order to combine information from multiple sensors effectively, we use the _Wasserstein Barycenter_ from Optimal Transport theory. Combining these tools together along with classic signal processing transformations such as the Welch transform, we have an end-to-end anomaly detection algorithm in both offline and online scenarios capable of accurately detecting transitions in a wide variety of contexts.

In order to demonstrate the algorithms we use, we have created a number of Jupyter notebook demonstrations. These are contained in the notebooks folder. We have the following: 
1. Baseline models. In this folder, we apply two classes of machine learning models used for classification (Feature Extraction->SVM and 1D Convolution Networks) to the damage classification problem. We use the performances from these models as benchmarks for the matrix profiling methods we will showcase, and also to contrast the benefits of an unsupervised noise-robust algorithm with supervised black-box models.
2. Offline. In this folder, we display an example of the end-to-end algorithm, starting with raw sensor data, applying transformations into the frequency domain and smoothing techniques, applying the Variational Mode Decomposition (VMD) and computing the matrix profile before ensembling the resulting curve together with the Wasserstein barycenter to produce a final estimate of anomalous transition positions. The resulting detector is able to demarcate all anomalous transitions with 100% accuracy.
3.  Online. In this folder, we display our extensions to the offline end-to-end algorithm to work with real-time data. As data-points arrive, the matrix profiles are able to be updated in a sequential fashion with low time complexity owing to the way the matrix profile is defined. By animating the resulting curves in time as data points are added in, we can visualise how the detector reacts to increasing damage in real-time. Our results show that all anomalous transitions are detected with 100% accuracy. The animations are included in the Jupyter notebook.

## Requirements and Installation
- Python >= 3.7.12 

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
This is preferred due to Tensorflow conflicts with other packages, especially if you are also using M1 chip Macbooks.
## 

