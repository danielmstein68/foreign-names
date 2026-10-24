# Replication Data for: "American Local Government Elections Database"
This file accompanies the datasets and replication code to reproduce the results in ÒAmerican Local Government Elections Database,Ó by Justin de Benedictis-Kessner, Diana Da In Lee, Yamil Velez, and Christopher Warshaw.

Analyses were carried out using R version 4.0.2 on a computer running Mac OS 11.7.3. All packages used for each script file are listed at the top of each script.

Random forest models were carried out using Python version 3.9.7 executed via Anaconda version 5.3.1 on a Linux-based high performance computing. All packages used for each script file are listed at the top of each script.

Instructions for replicators:
The included R script file reproduce the figures and tables included in the data descriptor paper, as well as the examples displayed in the ``Usage'' section of the paper. This script will output the associated figures and tables into two folders (which the script creates if they do not already exist) inside the same file directory where the script is stored: one called "figures," and one called "tables."


## Manifest of all files:

### Data files:

* ledb_candidatelevel.rds and ledb_candidatelevel.csv: main data files of local elections of various types at the candidate level, along with all associated candidate-level variables and moderating variables. Provided in both .rds and .csv formats.

* cities_historical_demographics.rds: files with historical information on overall population and racial and gender demographics in cities. Used for analyses in the ``Usage'' section of the paper to compare demographics of elected officials to the demographics of their communities.

* counties_historical_demographics.rds: files with historical information on overall population and racial and gender demographics in counties. Originally downloaded from NHGIS using decadal Census estimates as well as 2015-2019 estimates from the American Community Survey (ACS). Used for analyses in the ``Usage'' section of the paper to compare demographics of elected officials to the demographics of their communities.

* school_historical_demographics.rds: files with historical information on overall population and racial and gender demographics in school districts. Originally downloaded from NHGIS using 2015-2019 estimates from the American Community Survey (ACS). Used for analyses in the ``Usage'' section of the paper to compare demographics of elected officials to the demographics of their communities.

* citycouncils_comp.rds: data file with the partisan, racial, and gender composition of city councils over time, in places and years for which we had a full panel of all seats on the city council for those years (i.e. no missing data on individual seats on a council). Used for analyses and figures looking at the composition of city councils over time. This file can be created with the main script file (under the section ``Creating demographic composition panels'') or it can be loaded from this replication archive. As a warning: the creation of this composition file does not handle special elections that only replace a single seat of a multi-member district well, and may leave the number of total seats in a given year different from the number of elected candidates with known partisan/demographic information.

* countycouncils_comp.rds: data file with the partisan, racial, and gender composition of county councils over time, in places and years for which we had a full panel of all seats on the county council for those years (i.e. no missing data on individual seats on a council). Used for analyses and figures looking at the composition of county councils over time. This file can be created with the main script file (under the section ``Creating demographic composition panels'') or it can be loaded from this replication archive. As a warning: the creation of this composition file does not handle special elections that only replace a single seat of a multi-member district well, and may leave the number of total seats in a given year different from the number of elected candidates with known partisan/demographic information.

* schoolboards_comp.rds: data file with the partisan, racial, and gender composition of school boards over time, in places and years for which we had a full panel of all seats on the school board for those years (i.e. no missing data on individual seats on a board). Used for analyses and figures looking at the composition of school boards over time. This file can be created with the main script file (under the section ``Creating demographic composition panels'') or it can be loaded from this replication archive. As a warning: the creation of this composition file does not handle special elections that only replace a single seat of a multi-member district well, and may leave the number of total seats in a given year different from the number of elected candidates with known partisan/demographic information.

* data_gender_imputation_matrix_anonymized_230719.rds: main data file collapsed our data by name, city, and office with covariates relevant to candidate gender. 

* data_pid_imputation_matrix_anonymized_230719.rds: main data file collapsed our data by name, city, and office with candidates relevant to candidate party identification. 

* data_race_imputation_matrix_anonymized_230719.rds: main data file collapsed our data by name, city, and office with covariates relevant to candidate race/ethnicity. 

* df_gender.Rdata: pre-processed data file of data_gender_imputation_matrix_anonymized_230719.rds. Used to train a random forest model for gender prediction. This file can be created with the script file 0_preprocess.R located in the folder predictions/gender.

* df_pid.Rdata: pre-processed data file of data_pid_imputation_matrix_anonymized_230719.rds. Used to train a random forest model for party identification prediction. This file can be created with the script file 0_preprocess.R located in the folder predictions/party.

* df_race.Rdata: pre-processed data file of data_race_imputation_matrix_anonymized_230719.rds. Used to train a random forest model for race/ethnicity prediction. This file can be created with the script file 0_preprocess.R located in the folder predictions/race.


### Script files:

* descriptives_and_usage.R: script to reproduce the main descriptive analyses in the paper and associated figures and tables.

* 0_preprocess.R: script that calls and pre-processes raw data in preparation of running a random forest model for gender, party, and race/ethnicity. The script under the same filename exists for each prediction attribute, located in the subfolders under predictions. 

* 1_rf.py: script that performs random forest classification for gender, party, and race/ethnicity. Outputs a prediction result in csv containing predicted probabilities for each attribute category included in the main file. The script under the same filename exists for each prediction attribute, located in the subfolders under predictions. See Logs.txt located within each subfolder for the cross-validation results.

* 2_validate.R:	script that runs performance evaluation (Tables 4-6), ROC, and variable importance permutation test of the random forest classification results for gender, party, and race/ethnicity. Relies on the prediction result created in 1_rf.py. The script under the same filename exists for each prediction attribute, located in the subfolders under predictions. 



## Data sources:

Population demographic data were downloaded from NHGIS and merged to create historical demographics files used here:

Steven Manson, Jonathan Schroeder, David Van Riper, Tracy Kugler, and Steven Ruggles. 
        IPUMS National Historical Geographic Information System: Version 16.0 
        [dataset]. Minneapolis, MN: IPUMS. 2021. 
        http://doi.org/10.18128/D050.V16.0



	