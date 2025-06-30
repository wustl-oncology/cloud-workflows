#!/usr/bin/env python3

import os
import yaml
import subprocess
import argparse
import re

def is_gs_path(path):
    return path.startswith("gs://")

def file_exists(path):
    if is_gs_path(path):
        try:
            subprocess.check_call(["gsutil", "-q", "stat", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False
    elif path.startswith("/"):
        return os.path.exists(path)
    return False

def flatten_file_paths(yaml_dict):
    paths = []

    def recurse(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                recurse(v)
        elif isinstance(obj, list):
            for item in obj:
                recurse(item)
        elif isinstance(obj, str) and (obj.startswith("gs://") or obj.startswith("/")):
            paths.append(obj)

    recurse(yaml_dict)
    return paths

def extract_rg_field(readgroup_str, field):
    pattern = fr"{field}:([^\t\\]+)"
    match = re.search(pattern, readgroup_str)
    return match.group(1) if match else None

def check_commenting_issues(yaml_text):
    lines = yaml_text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"#\s*immuno\.problematic_amino_acids\s*:", line):
            j = i + 1
            while j < len(lines) and not re.match(r"^\s*immuno\.", lines[j]):
                if re.match(r"^\s*-\s+\S", lines[j]):
                    print(f"Improperly commented list item after commented key on line {i+1}: '{lines[j].strip()}'")
                    break
                j += 1

def check_empty_active_keys_with_commented_lists(yaml_text):
    lines = yaml_text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^\s*immuno\.\w+:\s*$", line):  # active key, no value
            key_line = line.strip()
            key_indent = len(line) - len(line.lstrip())
            has_active_item = False
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent <= key_indent and re.match(r"^\s*\w", next_line):
                    break
                if re.match(r"^\s*-\s+\S", next_line):  # active item
                    has_active_item = True
                    break
                j += 1
            if not has_active_item:
                print(f"Key '{key_line}' appears active but has only commented-out list items (or none).")

def is_proper_fastq_pair(fq1, fq2):
    fq1_base = os.path.basename(fq1)
    fq2_base = os.path.basename(fq2)
    patterns = [
        ("_1.fastq.gz", "_2.fastq.gz"),
        ("_1.fq.gz", "_2.fq.gz"),
        (".R1.fastq.gz", ".R2.fastq.gz"),
        (".R1.fq.gz", ".R2.fq.gz"),
        ("-1.fastq.gz", "-2.fastq.gz"),
        ("-1.fq.gz", "-2.fq.gz"),
    ]
    for r1, r2 in patterns:
        if fq1_base.endswith(r1) and fq2_base.endswith(r2):
            if fq1_base.replace(r1, "") == fq2_base.replace(r2, ""):
                return True
    if fq1_base.replace("_1", "_2") == fq2_base:
        return True
    if fq1_base.replace("R1", "R2") == fq2_base:
        return True
    if fq1_base.replace("-1", "-2") == fq2_base:
        return True
    return False

def check_commented_blocks(yaml_text):
    results = []
    checks = {
        'problematic_amino_acids': {
            'keyword': 'immuno.problematic_amino_acids:',
            'no_text_message': "No problematic amino acids in this run",
            'has_text_message': "Problematic amino acids selected:"
        },
        'clinical_mhc_classI_alleles': {
            'keyword': 'immuno.clinical_mhc_classI_alleles:',
            'no_text_message': "Class I HLA alleles commented out",
            'has_text_message': "Class I HLA alleles selected:"
        },
        'clinical_mhc_classII_alleles': {
            'keyword': 'immuno.clinical_mhc_classII_alleles:',
            'no_text_message': "Class II HLA alleles commented out",
            'has_text_message': "Class II HLA alleles selected:"
        }
    }
    lines = yaml_text.splitlines()
    for check_name, check_info in checks.items():
        found = False
        for idx, line in enumerate(lines):
            if check_info['keyword'] in line:
                found = True
                if line.strip().startswith('#'):
                    results.append(check_info['no_text_message'])
                else:
                    results.append(check_info['has_text_message'])
                    j = idx + 1
                    while j < len(lines):
                        next_line = lines[j].strip()
                        if next_line.startswith('#') or next_line.startswith('immuno.'):
                            break
                        if next_line:
                            results.append(f"  {next_line}")
                        j += 1
                break
        if not found:
            results.append(f"{check_name} not found in YAML")
    return results

def validate_yaml(yaml_file):
    print(f"Validating: {yaml_file}\n")

    try:
        with open(yaml_file) as f:
            yaml_text = f.read()
            data = yaml.safe_load(yaml_text)
    except Exception as e:
        print(f"Failed to read or parse YAML: {e}")
        return

    immuno = {k[len("immuno.") :]: v for k, v in data.items() if k.startswith("immuno.")} 
    if not immuno:
        print("Error: No keys starting with 'immuno.' were found.") 
        return

    print("Checking file paths...")
    paths = flatten_file_paths(immuno) 
    missing = [p for p in paths if not file_exists(p)] 
    if missing:
        print("Missing file paths:") 
        for p in missing:
            print(f" - {p}") 
    else:
        print("All file paths exist.") 

    print("\nChecking for duplicate file paths...")
    duplicates = set([p for p in paths if paths.count(p) > 1]) 
    if duplicates:
        print("Duplicate file paths:") 
        for p in duplicates:
            print(f" - {p}") 
    else:
        print("No duplicate file paths found.") 

    print("\nChecking FASTQ pairings...")
    for group in ['tumor_sequence', 'normal_sequence', 'rna_sequence']: 
        sequences = immuno.get(group, []) 
        for i, seq in enumerate(sequences):
            s = seq["sequence"] 
            fq1, fq2 = s["fastq1"], s["fastq2"] 
            if not is_proper_fastq_pair(fq1, fq2): 
                print(f"Pairing mismatch in {group} entry {i+1}:") 
                print(f"   fastq1: {fq1}") 
                print(f"   fastq2: {fq2}") 

    print("\n Checking readgroup SM fields...")
    expected_sms = { #
        "tumor_sequence": immuno.get("tumor_sample_name"), 
        "normal_sequence": immuno.get("normal_sample_name"), 
        "rna_sequence": immuno.get("sample_name"), 
    }
    for group, expected_sm in expected_sms.items(): 
        sequences = immuno.get(group, []) 
        for i, seq in enumerate(sequences): 
            rg = seq["readgroup"] 
            actual_sm = extract_rg_field(rg, "SM") 
            if actual_sm != expected_sm: 
                print(f"SM mismatch in {group} entry {i+1}: expected '{expected_sm}', found '{actual_sm}'") 

    print("\nRNA CN fields:") 
    for seq in immuno.get("rna_sequence", []): 
        rg = seq["readgroup"] 
        cn = extract_rg_field(rg, "CN") 
        print(f" - CN: {cn}") 
    print(f"Strand: {immuno.get('strand')}") 

    print("\nChecking for improperly commented list items...") 
    check_commenting_issues(yaml_text) 
    check_empty_active_keys_with_commented_lists(yaml_text) 

    # Call the new function and print its results
    print("\nChecking commented blocks status:")
    comment_block_results = check_commented_blocks(yaml_text)
    for result in comment_block_results:
        print(result)

    print("\nValidation complete.") 

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate an immuno YAML file for common formatting and logic errors.") 
    parser.add_argument("yaml_file", help="Path to the YAML file to validate.") 
    args = parser.parse_args() 

    validate_yaml(args.yaml_file) 
