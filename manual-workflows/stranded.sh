bsub -q general-interactive -G compute-mgriffit -n 1 -M 32G -R 'select[mem>32G] span[hosts=1] rusage[mem=32G]' -Is -a 'docker(mgibio/checkstrandedness:v1)' /bin/bash
check_strandedness --print_commands \
	--gtf /storage1/fs1/mgriffit/Active/griffithlab/common/reference_files/human_GRCh38_ens105/rna_seq_annotation/Homo_sapiens.GRCh38.105.gtf \
	--kallisto_index /storage1/fs1/mgriffit/Active/griffithlab/common/reference_files/human_GRCh38_ens105/rna_seq_annotation/Homo_sapiens.GRCh38.cdna.all.fa.kallisto.idx \
	--reads_1 /storage1/fs1/mgriffit/Active/immune/j.yao/Miller/raw_data/Hu_048/Hu_048_tumor_rna_SRR24836175/SRR24836175_1.fastq \
	--reads_2 /storage1/fs1/mgriffit/Active/immune/j.yao/Miller/raw_data/Hu_048/Hu_048_tumor_rna_SRR24836175/SRR24836175_2.fastq -n 100000 > ../../trimmed_read_strandness_check.txt
