sumcoresg
=========

Code written by Zhuyi Xue (alfred532008@gmail.com), with minor additions by Chris Ing (ing.chris@gmail.com)

A web application for CPU usage tracking on HPC resources. A successor to [JobOverseer](https://github.com/pomeslab/JobOverseer), but still woefully lacking lots of great features. 
This code is designed to run on Heroku. It works by using SSH authentication and scraping results of commands sent to a series of HPC head nodes. It's primarily a proof-of-concept and should be only used with great discretion.
