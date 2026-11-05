# DANDI:000004 session `sub-P19HMH_ses-20080601_obj-uw5up9_ecephys+image.nwb`

Subject P19HMH; NWB schema 2.1.0; 16 units; 150 trials.

## NWB Inspector (config: dandi)

| Level | Count |
|---|---|
| BEST_PRACTICE_SUGGESTION | 6 |
| BEST_PRACTICE_VIOLATION | 2 |
| CRITICAL | 2 |
| ERROR | 1 |
| PYNWB_VALIDATION | 6 |

| Level | Check | Location | Message |
|---|---|---|---|
| ERROR | During evaluation of 'check_units_table_duration' - <class 'TypeError'>: Indexing arrays must have integer dtypes |  | Traceback (most recent call last): File ".\.venv\Lib\site-packages\nwbinspector\_nwb_inspection.py", line 471, in  |
| PYNWB_VALIDATION | VectorIndex/description | units/spike_times_index | argument missing |
| PYNWB_VALIDATION | VectorIndex | units/spike_times_index | incorrect type - expected 'uint8', got 'int32' |
| PYNWB_VALIDATION | Units/spike_times_index | units/spike_times_index | incorrect type - expected 'uint8', got 'int32' |
| PYNWB_VALIDATION | VectorIndex/description | units/electrodes_index | argument missing |
| PYNWB_VALIDATION | VectorIndex | units/electrodes_index | incorrect type - expected 'uint8', got 'int32' |
| PYNWB_VALIDATION | Units/electrodes_index | units/electrodes_index | incorrect type - expected 'uint8', got 'int32' |
| CRITICAL | check_subject_age | /general/subject | Subject age, '34', does not follow ISO 8601 duration format, e.g. 'P2Y' for 2 years or 'P23W' for 23 weeks. You may also specify a range using a '/' separator,  |
| CRITICAL | check_subject_species_form | /general/subject | Subject species 'Human' should either be in Latin binomial form (e.g., 'Mus musculus' and 'Homo sapiens') or be a NCBI taxonomy link (e.g., 'http://purl.obolibr |
| BEST_PRACTICE_VIOLATION | check_units_resolution_is_set |  | Units table has spike_times but resolution is not set. Resolution indicates the smallest possible difference between two spike times and should be a positive fl |
| BEST_PRACTICE_VIOLATION | check_data_orientation | /stimulus/presentation/StimulusPresentation | Data may be in the wrong orientation. Time should be in the first dimension, and is usually the longest dimension. Here, another dimension is longer. Current sh |
| BEST_PRACTICE_SUGGESTION | check_description | /general/devices/Neuralynx-cheetah | Description is missing. |
| BEST_PRACTICE_SUGGESTION | check_description | /stimulus/presentation/StimulusPresentation | Description ('no description') is a placeholder. |
| BEST_PRACTICE_SUGGESTION | check_small_dataset_compression | /stimulus/presentation/StimulusPresentation | data is not compressed. Consider enabling compression when writing a dataset. |
| BEST_PRACTICE_SUGGESTION | check_experimenter_exists | / | Experimenter is missing. |
| BEST_PRACTICE_SUGGESTION | check_doi_publications | / | Metadata /general/related_publications 'Faraut et al. 2018, Scientific Data; Rutishauser et al. 2015, Nat Neurosci;' does not start with 'doi: ###' and is not a |
| BEST_PRACTICE_SUGGESTION | check_col_not_nan |  | Column 'imp' has all NaN values. Consider removing it from the table. |

## New/old labels against the images

Column description in the file: "The Ground truth Labels for New or Old Stimulus. 0 == Old Stimuli (presented during the learning phase), 1 = New Stimuli (not seen )'during learning phase"

| new_old_labels_recog | image shown in learning phase | trials |
|---|---|---|
| 0 | False | 50 |
| 1 | False | 24 |
| 1 | True | 26 |

