# MOFDiscovery
## 1. Introduction
##### step 1: In the MOFdiscovery project, we will first use ```MOFs_extraction.py``` to extract the descriptors, smiles, geometric data, and other properties of 3D MOFs (from CCDC MOF dataset), and the results will be saved as a csv file. 
##### step 2: Then we will use the ```packing scripts``` to do the packing for all the 3D MOFs, and the results will be saved as mol2 file and will be the input file for next calculation. 
##### step 3: Dock the 3D MOF with some small amino acid by using Gold (since it includes a large dataset, so we will use ccdc python api). the scripts in ```docking folder``` are used for docking in local computer. and the scripts in ```Gold_Cluster_Computing``` are used for HPC. then we will get the results such as the best ranked poses, the scores (depend on the score function we use).
##### step 4: after the docking process, we will use ```Full interaction map scripts``` to investigate the reason for the docking and example it. we could also use Hermes to achieve this goal. And the result of this script will be a map. (the script is not ready yet)
##### The details of every scripts are shown on the 3rd part - ```'explanation of scripts'```


## 2. Tutorial
### 2.1 Prepare the dataset
As mentioned in the introduction. we will have two dataset: 1. **3D MOF dataset** 2. **oligopeptide dataset**. the result from the step 1 is shown on this picture and this is the 3D MOF Geometric Dataset. It include all the MOF data from CCDC MOF dataset. Then we extract the 3D MOF mol2 file from ConQuest, and they will be the input file for the docking process. The oligopeptide mol2 file will be the input file of ligands for the docking process.
![image](https://github.com/ZiedHosni1/MOF_discovery/assets/152184609/21b15e98-4b14-438a-b3f0-f5829416ce0a) 

### 2.2 Installation
The python version we use is 3.9.0, and the software we need is CCDC ConQuest, Mercury, Hermes and Gold. Since we need to run the scripts for these softwares, so we also need CCDC Python API. And If we want to run the scripts on HPC, we also need the Gold_Cluster_Computing. 

## 3. explanation of the scripts:
### 3.1 MOFs_extraction script
1. **Overview**: The input files are the MOF_subset dataset from CCDC Dataset, it includes 125,383 MOFs. And this script could be used to extract many properties of MOFs by using csd python api, such as smiles, solubility, cell volume, density and so on. The output results will be saved as a csv.file.
2. ```
   def extract_mof_properties(n):
    # Initialize CSD connection and read MOF subset
    mof_reader = EntryReader(subset=Subsets.MOF)

    # Open a CSV file to write the data with UTF-8 encoding
    with open('mof_properties.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['refcode'] + properties
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
this part of the script sets up the extraction of MOF properties from a database and prepares a CSV file to store the extracted data.

3. ```
   print(f"MOF properties extraction completed for {n} entries and saved to mof_properties.csv.")
   extract_mof_properties(100)
this is an example usage about extracting properties for 100 MOF entries, and you could change "n" to the number of MOFs you want to extract. And if you want to extract the properties of all the MOF_subset, you could change "n" to "125383".
##### for more information you could download this dataset from the following link: https://drive.google.com/file/d/1ZObphXu1UuyVUNuhCC8NzB7HawmNUVUF/view?usp=drive_link.

### 3.2 Packing script: (I need your help about the packing scripts :))
1. **Overview**: the input file is the 3D MOF list, and we will use the script to do the packing of them and prepare for the next docking process.
2. ```def packing(self, box_dimensions=((0, 0, 0), (1, 1, 1)), inclusion='CentroidIncluded'):``` the function of this script is to fill some multiple of the unit cell of the crystal (packing). and **'CentroidIncluded'** means where whole molecules will be included if their centroid is within the box dimensions (you could change it to 'AllAtomsIncluded' 'AnyAtomIncluded' or 'OnlyAtomsIncluded'). The **'ccdc.crystal.Crystal.packing()'** method takes two optional arguments: the size of the box to pack and an inclusion criterion. The box dimensions are a pair of triples of floats, being the near corner and far corner of the box in terms of multiples of the unit cell. the default setting of Mercury is (0, 0, 0), (1, 1, 1), and from CCDC examples, we could also change it to (-2, -2, -2), (2, 2, 2).
3. ```csv = ChemistryLib.CrystalStructureView_instantiate(self._csv)psv = ChemistryLib.CrystalStructurePackingView(csv)``` I think it is about the ChemistryLib from CCDC, I am not quite sure about this step.
4. ``` if psv.packable():
        csv.set_inclusion_condition(self._decode_inclusion(inclusion))
        box = MathsLib.Box(box_dimensions[0], box_dimensions[1])
        psv.set_packing_box(box)
        psv.set_packing(True)
this part is to check the packability and creat a packing Box. 
the def function I copied from CCDC, and I think I need to import_ccdc_module('ChemistryLib') and import_ccdc_module('MathsLib') first, but I am confused about this part. 
##### the def packing script I copied from the following link: https://downloads.ccdc.cam.ac.uk/documentation/API/_modules/ccdc/crystal.html#Crystal.packing 
##### and for other packing information you can check https://downloads.ccdc.cam.ac.uk/documentation/API/descriptive_docs/crystal.html#packing-and-slicing.
### 3.3 Docking scripts:
#### 3.3.1 Docking scripts for local computer
1. **Overview**: These scripts could help to you to do the docking with MOFs and ligands for large dataset. And could be used in your local computer. for the old scripts **Gold_multi_map and Gold_multi_queue 1** and new script **gold_multi**, they are used for docking 1 MOF with many different ligands. And for the scripts **Chatgpt modified queue 1 and Chatgpt modified new gold_multi**, they could be used to dock many MOFs with 1 ligand, this could help you to choose the MOF with large volume you want.
2. Original scripts about docking 1 protein or MOF with many ligands(**Gold_multi_map and Gold_multi_queue 1**), these two scripts are from CCDC Gold instruction but they are too old.
3. **gold_multi**: the new script the CCDC support team sent to me, it has the same function as the first two scripts.
4. I used the Chatgpt help me to modify the Gold_multi_queue1 and the new gold_multi script and try to make it possible to use these scripts to do the docking with many MOFs to one ligand, and I used the **function to name these scripts** you could find them in **docking** folder.
5. conclusion: the input file for docking: MOF mol2 file, ligand file (some oligopeptide from my dataset), gold_conf. and the output path depends on the gold_conf??? (**I couldn't find where is it in my gold_conf so this is a problem**)
#### 3.3.2 Docking scripts for HPC
1. **Overview**: These scripts could be used for using CCDC Gold in HPC (High Performance Computing).
2. **'cluster.ini'** is used to define the settings for a docking job. This includes paths to input files, batch sizes, and SLURM-specific options such as job name, partition, and time limits.
3. **'cluster_batching.py'** This script partitions ligands into regular-sized batches, bundling them with other required files into .tar.gz format. These batches are then used during the docking run.
4. **'cluster_batching.sh'** Submit this script via Slurm to perform ligand batching on a cluster node.
5. **'cluster_collect.py'** Generates an ordered file containing fitness scores and creates a directory with solution molfiles if requested.
6. **'cluster_docking.py'** this script is to process batches of ligands for docking using the GOLD software, leveraging the goldhpc module.
7. **'cluster_monitor.py'** Allows checking the status of running jobs without affecting them.
8. **'cluster_resume.py'** Enables the job to pick up from where it left off.
9. **'cluster_start.py'** Demonstrates the order of a full docking run and can be used as a convenience to run all necessary steps sequentially.
10. **'cluster_status.py'** Provides detailed information about the status of all sub-jobs or a specific job ID.
11. **'cluster_stop.py'** Allows stopping of a running job, which will automatically start the next pending job if any.
12. **'cluster_submit.py'** Handles submission of large jobs by automatically splitting them into multiple sub-jobs if necessary.
13. **'cluster_timing.py'** Provides information about the time taken for various stages of the job.
14. **'goldhpc'** is a module designed to support high-performance computing (HPC) workflows for the GOLD docking software, particularly in a cluster environment.
15. **'goldqueue_2022'** **this file is too large, and I didn't upload it to github**. And it is a Singularity image file that encapsulates the GOLD software and its dependencies. Singularity is a container platform that allows users to package applications and their dependencies into a single file (called an image), which can be easily transported and run on different environments without worrying about system compatibility issues.




       
