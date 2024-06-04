import os
import threading

import wave
import pickle

import librosa as lbr
import numpy as np
import pandas as pd
from tqdm import tqdm
import matplotlib.pyplot as plt

from cqt_trim_enum import CQTTrimMethod, trim_CQT

# constants for quick config
GRAPH = False  # set to True to display the CQT graphs
CQT_TRIM_METHOD = (
    CQTTrimMethod.THRESHOLD
)  # set to trim_CQT_thresh to trim by threshold instead of time slice

labels = None
cqt_data = (
    pd.DataFrame()
)  # data frame to store the cqt data. LABEL, CQT_DATA_TRIMMED, CQT_DATA_FULL


def read_wav(file):
    """Read data from the audio files individually, obtaining information on the dat itself and frame/sample rate"""
    with wave.open(file, "r") as f:
        audio_data = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16)
        audio_data_float, sample_rate = lbr.load(file)
        frame_rate = f.getframerate()
    return audio_data, audio_data_float, frame_rate, sample_rate


def cqt_func(audio_data, frame_rate):
    """
    Simulates the CQT (Constant Q Transformation) and returns the data,
    which consists of varying frequencies (in Hz) and their time durations
    """
    cqt_data = np.abs(
        lbr.cqt(
            audio_data,
            sr=frame_rate,
            bins_per_octave=48,  # bins_per_octave and n_bins both control resolution of image.
            fmin=lbr.note_to_hz("A2"),  # sets the lower bound of collected notes
            n_bins=288,  # for a whole number of octaves to be displayed, must be a multiple of bins_per_octave
        )
    )  #  n_bins=480, bins_per_octave=96
    return cqt_data


def plot_cqt_data(cqtd, sample_rate, label, ind):
    """
    Creates a CQT display and uploads the image into a ./cqt_graphs/ folder. It displays the
    time vs frequencies (frequencies can be shown in Hz or letter pitch, e.g. 110 Hz or A2).
    Each audio file has its respective CQT plot respectively in the CQT graphs folder. Purely for visulization;
    Visulizations are meant to be viewed in a developer env.
    """
    if GRAPH:
        fig, ax = plt.subplots()
        img = lbr.display.specshow(
            lbr.amplitude_to_db(cqtd, ref=np.max),
            y_axis="cqt_note",  # change this param to switch between showing frequncies in Hz or its pitch
            sr=sample_rate,
            x_axis="ms",
            ax=ax,
            bins_per_octave=48,  # controls the scaling to the resolution of images.
            fmin=lbr.note_to_hz(
                "A2"
            ),  # tries to set the lower bound of frequencies displayed on the y axis
        )
        ax.set_title(f"Constant-Q power spectrum + pitch of {label}")
        fig.colorbar(
            img, ax=ax, format="%+2.0f dB"
        )  # creates a color bar to map the CQT diagrams with relative strengths.
        plot_file_name = f"./cqt_graphs/{label}/{label}-v{ind}.jpg"
        # save files into a CQT diagram folder
        if not os.path.exists(plot_file_name):
            plt.savefig(plot_file_name)


# create the CQT graphs folder, used y the plot_cqt_data function
if not os.path.exists("./cqt_graphs"):
    os.mkdir("./cqt_graphs")

# checks if the pickled data file has been created or not and considers the case it not created
if not os.path.exists("./pickled_data/data.pkl"):
    if not os.path.exists("./pickled_data"):
        os.mkdir("./pickled_data")  # If the dir does not exist, create it
    labels = [
        i.name for i in os.scandir("./data") if i.is_dir()
    ]  # obtain the note labels from the data folder, 42-43 of them
    labels.sort()

    # starts reading the .wav files form the data dir
    for label in tqdm(
        labels, desc="Reading wav files"
    ):  # moves thru the 42 labels while producing a viewable progress bar
        # Obtain a list of strings of the .wav file names and their relative paths under the folder named with the note described by "label"
        wav_files = [
            f"./data/{label}/{i.name}"
            for i in os.scandir(f"./data/{label}")
            if i.is_file() and i.name.endswith(".wav")
        ]
        # Instantiates lists to group together CQT data from audio files under the same note
        _cqt_data_labels = []
        _cqt_data_trimmed = []
        _cqt_data_full = []
        # creates the file path directory for the respective note described by "label" in the cqt graphs dir
        label_fp = f"./cqt_graphs/{label}"  # fp - file path
        if not os.path.exists(label_fp):
            os.mkdir(label_fp)  # creates the dir if it does not already exist
        # Loop thru wav files as tuples of (index, file)
        for ind, wav in enumerate(wav_files):
            wav_data, wdf, wr, sr = read_wav(
                wav
            )  # wav data, wav data in float, wave rate, sample rate respectively
            # using data obtained from reading wav file, run cqt and obtain their corresponding data
            cqt_datum = cqt_func(wdf, sr)
            plot_cqt_data(
                cqt_datum, sr, label, ind + 1
            )  # plot the cqt data for the wav file under the note described by "label"

            trimmed_data = trim_CQT(CQTTrimMethod, cqt_datum)  # trim data

            # update columns
            _cqt_data_full.append(cqt_datum)
            _cqt_data_trimmed.append(trimmed_data)
            _cqt_data_labels.append(label)
        # append data for cqt for the label to the overall lists representing all the cqt data repectively
        new = pd.DataFrame(
            {
                "LABEL": _cqt_data_labels,
                "CQT_DATA_TRIMMED": _cqt_data_trimmed,
                "CQT_DATA_FULL": _cqt_data_full,
            }
        )
        cqt_data = pd.concat([cqt_data, new], ignore_index=True)
    # upload data locally into pickled binary files to be loaded in for later use
    cqt_data.to_pickle("./pickled_data/data.pkl")
else:
    # read already created cqt data
    cqt_data = pd.read_pickle("./pickled_data/data.pkl")

if __name__ == "__main__":
    # print the cqt head
    print(cqt_data.head())
