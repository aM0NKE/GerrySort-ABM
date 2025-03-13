#!/bin/bash
#SBATCH --exclusive
#SBATCH --time=12:00:00
#SBATCH -N 2
#SBATCH --ntasks-per-node=16
#SBATCH -C cpunode

source ~/miniconda3/bin/activate gerrysort

mpirun python3 runMPI_global_sensitivity.py