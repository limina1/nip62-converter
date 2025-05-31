#!/usr/bin/env python3
"""
Script to organize loose .adoc files into proper directory structure
for NKBIP-01 compliance
"""

import os
import shutil
from pathlib import Path

# Define file mappings
FILE_MAPPINGS = {
    'content/research/consciousness': [
        'An information integration theory of consciousness.adoc',
        'Brain networks predict metabolism, diagnosis and prognosis at the bedside in disorders of consciousness.adoc',
        'Cognitive Motor Dissociation in Disorders of Consciousness.adoc',
        'Conscious Processing and the Global Neuronal Workspace Hypothesis.adoc',
        'Covert Cognition in Disorders of Consciousness: A Meta-Analysis.adoc',
        'Covert Tracking to Immersive Stimuli in Traumatic Brain Injury Subjects With Disorders of Consciousness.adoc',
        'Covert consciousness.adoc',
        'Detecting Awareness in the Vegetative State.adoc',
        'Detection of Brain Activation in Unresponsive Patients with Acute Brain Injury.adoc',
        'Early detection of consciousness in patients with acute severe traumatic brain injury.adoc',
        'Functional and structural brain connectivity in disorders of consciousness.adoc',
        'Information Sharing in the Brain Indexes Consciousness in Noncommunicative Patients.adoc',
        'MRI in disorders of consciousness.adoc',
        'Prognosis of consciousness disorders in the intensive care unit.adoc',
        'Recovery from disorders of consciousness: mechanisms, prognosis and emerging therapies.adoc',
        'Recovery of consciousness after acute brain injury: a narrative review.adoc',
        'The Quest for Covert Consciousness.adoc',
        'What names for covert awareness? A systematic review.adoc'
    ],
    'content/research/health': [
        'AzraRazaCancer.adoc',
        'Comprehensive Review on Alzheimer\'s Disease: Causes and Treatment.adoc',
        'Doing more with less: our decade of experience with laparo-endoscopic single site Heller myotomy supports its application.adoc',
        'guidetohealth00gandrich2.adoc'
    ],
    'content/knowledge': [
        'living_knowledge.adoc'
    ],
    'content/media': [
        'Currents 044: Zak Stein on Propaganda and the Information War - The Jim Rutt Show.adoc',
        'EP 296 Ashley Hodgson on Economic Mythology and System Change - The Jim Rutt Show.adoc',
        'We Need Ruminant Animals, Carnivorism, Surprising Statistics | Peter Ballerstedt PhD | Dr. Fernando Morales Podcast.adoc'
    ],
    'examples/samples': [
        'NostrApps101.adoc',
        'BuildingApollo.adoc'
    ]
}

def organize_files(dry_run=True):
    """Move files to their proper locations"""
    moves = []
    
    for target_dir, files in FILE_MAPPINGS.items():
        target_path = Path(target_dir)
        
        # Ensure target directory exists
        if not dry_run:
            target_path.mkdir(parents=True, exist_ok=True)
        
        for filename in files:
            source = Path(filename)
            if source.exists():
                destination = target_path / filename
                moves.append((source, destination))
                
                if dry_run:
                    print(f"Would move: {source} -> {destination}")
                else:
                    shutil.move(str(source), str(destination))
                    print(f"Moved: {source} -> {destination}")
            else:
                print(f"Warning: File not found: {filename}")
    
    return moves

def main():
    """Main function"""
    print("NKBIP-01 Content Organization Script")
    print("====================================\n")
    
    # First do a dry run
    print("Dry run - showing what would be moved:")
    print("-" * 40)
    moves = organize_files(dry_run=True)
    
    if not moves:
        print("No files to move!")
        return
    
    print(f"\nTotal files to move: {len(moves)}")
    
    # Ask for confirmation
    response = input("\nProceed with moving files? (y/N): ")
    if response.lower() == 'y':
        print("\nMoving files...")
        organize_files(dry_run=False)
        print("\nOrganization complete!")
    else:
        print("Operation cancelled.")

if __name__ == "__main__":
    main()