import numpy as np
import pandas as pd

pd.options.mode.chained_assignment = None  # default='warn'

transition_counts = pd.DataFrame()
transition_mtx = pd.DataFrame()
num_transitions = 0


# ingest chord labels from Christopher Harte: http://isophonics.net/content/reference-annotations-beatles
def read_chord_labels(chordlabfile):
    df_chords = pd.read_csv(
        chordlabfile, sep=" ", names=["start_time", "stop_time", "chord"], header=None
    )
    return df_chords


# ingest section labels from same dataset
def read_section_labels(seglabfile):
    df_sections = pd.read_csv(
        seglabfile,
        sep="\t",
        names=["start_time", "stop_time", "empty", "section"],
        header=None,
    )
    return df_sections


# represent the "vocabulary" of all chords used in the song
def get_state_space(df, field):
    states = sorted(df[df.columns[field]].unique())
    return states


# helper function for generating the output sequence
def generate_chord_index(current_chord_idx, tm):
    xk = np.arange(len(tm))
    return np.random.choice(xk, 1, p=tm[current_chord_idx, :])[0]


# the heart of it: build the markov model transition matrix
def build_transition_matrix(df, debug):
    chord_labels = get_state_space(df, 2)
    # check that dataframe is not a single row / one chord
    if len(chord_labels) == 1:
        df["next_chord"] = df["chord"]
        transition_mtx = pd.DataFrame(index=chord_labels, columns=chord_labels)
        transition_mtx.iloc[0] = 1.0
        return transition_mtx, chord_labels

    df["next_chord"] = df["chord"].shift(-1)
    df.drop(df.tail(1).index, inplace=True)
    if debug:
        print("\nTransition data:")
        print(df)
    groups = df.groupby(["chord", "next_chord"])
    # https://stackoverflow.com/questions/55492109/how-to-create-a-transition-matrix-for-a-column-in-python
    # counts = {i[0]:len(i[1]) for i in groups} # count (A,A)
    counts = {
        i[0]: (len(i[1]) if i[0][0] != i[0][1] else 0) for i in groups
    }  # don't count (A,A)
    transition_counts = pd.DataFrame(index=chord_labels, columns=chord_labels)
    for x in chord_labels:
        transition_counts[x] = pd.Series(
            [counts.get((x, y), 0) for y in chord_labels], index=chord_labels
        )

    if debug:
        print("\nTransition counts:")
        print(transition_counts)

    # prepare square transition matrix with chord labels
    transition_mtx = pd.DataFrame(index=chord_labels, columns=chord_labels)
    for x in range(0, len(chord_labels)):
        if transition_counts.iloc[x].sum() == 0:
            transition_mtx.iloc[x] = 1.0 / len(chord_labels)
        else:
            transition_mtx.iloc[x] = (
                transition_counts.iloc[x] / transition_counts.iloc[x].sum()
            )

    if debug:
        print("\nTransition matrix:")
        print(transition_mtx)
    return transition_mtx, chord_labels


# generate an output
def generate_sequence(file, sequence_length, initial_chord):
    df = read_chord_labels(file)
    # compute transition matrix
    tm, chord_labels = build_transition_matrix(df, False)
    tm_np = tm.to_numpy(dtype=float)

    if not sequence_length:
        sequence_length = 8

    # initialize sequence with a random choice
    output = ["N" for i in range(sequence_length)]
    if not initial_chord:
        if df["chord"][0] == "N" and len(df.index) > 1:
            output[0] = df["chord"][1]
        else:
            output[0] = df["chord"][0]
    else:
        seed = chord_labels.index(np.random.choice(chord_labels, None))
        output[0] = chord_labels[seed]
        while output[0] == "N":
            output[0] = chord_labels[
                generate_chord_index(chord_labels.index(output[0]), tm_np)
            ]

    for i in range(1, sequence_length):
        output[i] = chord_labels[
            generate_chord_index(chord_labels.index(output[i - 1]), tm_np)
        ]
        while output[i] == "N":
            output[i] = chord_labels[
                generate_chord_index(chord_labels.index(output[i - 1]), tm_np)
            ]

    return output, chord_labels, tm


# now combine section and chord data
def add_section_to_chord_labels(sectionlabfile, df_chords):
    df_sections = read_section_labels(sectionlabfile)
    df_total = df_chords
    df_total["section"] = ""

    # augment the chord dataframe with section data
    k = 0
    for i in range(0, df_chords.shape[0]):
        if (
            df_chords["start_time"][i] < df_sections["stop_time"][k]
            and df_total["section"][i] == ""
        ):
            # if df_chords['start_time'][i] < df_sections['stop_time'][k]:
            df_total["section"][i] = df_sections["section"][k]
        else:
            k = k + 1
            if k >= df_sections.shape[0]:
                df_total["section"][i] = df_sections["section"][k - 1]
                break
            else:
                df_total["section"][i] = df_sections["section"][k]

    return df_total


# to display the original sequence of sections
def get_original_order_of_sections(sectionlabfile):
    df = read_section_labels(sectionlabfile)
    return df["section"]


# to display the original sequence of chords
def get_original_chord_progression(chordlabfile):
    df = read_chord_labels(chordlabfile)
    return df["chord"]


# build markov transition matrices per section
def build_segmented_transition_matrices(df_total):
    section_labels = get_state_space(df_total, 3)

    # build individual dataframes for each section; sections may repeat at later times!
    dict_of_df = {}
    df_names = []
    for section in section_labels:
        if section == "silence":
            continue
        key_name = "df_" + section
        dict_of_df[key_name] = df_total[df_total["section"] == section]
        df_names.append(key_name)

    # now build their transition matrices
    dict_of_tm = {}
    for df_name in df_names:
        tm, chord_labels = build_transition_matrix(dict_of_df[df_name], False)
        tm_name = "tm_" + df_name
        dict_of_tm[tm_name] = tm
        # print(dict_of_tm[tm_name])

    return dict_of_df, dict_of_tm, section_labels


# generate chord progressions based on sections
def generate_segment_sequences(
    chordlabfile, seglabfile, sequence_length, randomize_initial_chord
):
    df_chords = read_chord_labels(chordlabfile)
    df_total = add_section_to_chord_labels(seglabfile, df_chords)
    # compute transition matrices
    dict_of_df, dict_of_tm, section_labels = build_segmented_transition_matrices(
        df_total
    )
    tm_names = list(dict_of_tm)
    df_names = list(dict_of_df)

    # print(dict_of_df)

    if not sequence_length:
        sequence_length = 8

    outputs = []
    chord_labs = []

    k = 0
    for tm in tm_names:
        chord_labels = list(dict_of_tm[tm].columns)
        tm_np = dict_of_tm[tm].to_numpy(dtype=float)
        df_chords_section = dict_of_df[df_names[k]]
        k = k + 1
        output = ["N" for i in range(sequence_length)]

        # initialize sequence with original chord unless user specifies to initialize randomly
        if not randomize_initial_chord:
            if (
                df_chords_section["chord"].iloc[0] == "N"
                and len(df_chords_section.index) > 1
            ):
                output[0] = df_chords_section["chord"].iloc[1]
            else:
                output[0] = df_chords_section["chord"].iloc[0]
        else:
            seed = chord_labels.index(np.random.choice(chord_labels, None))
            output[0] = chord_labels[seed]
            while output[0] == "N":
                output[0] = chord_labels[
                    generate_chord_index(chord_labels.index(output[0]), tm_np)
                ]

        for i in range(1, sequence_length):
            output[i] = chord_labels[
                generate_chord_index(chord_labels.index(output[i - 1]), tm_np)
            ]
            while output[i] == "N":
                output[i] = chord_labels[
                    generate_chord_index(chord_labels.index(output[i - 1]), tm_np)
                ]

        outputs.append(output)
        chord_labs.append(chord_labels)

    section_labels.remove("silence")

    return outputs, chord_labs, section_labels, dict_of_tm, tm_names
