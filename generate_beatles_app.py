# import music21 as m21
# from music21 import midi
# from music21 import stream
import streamlit as st
import os
from transition import (
    generate_sequence,
    generate_segment_sequences,
    get_original_order_of_sections,
    get_original_chord_progression,
)


def app():
    st.title("Generating New Beatles Songs with Markov Chains")

    st.text("By Gina Collecchia, 8/12/2023")

    st.subheader("Introduction")
    harte_url = "http://isophonics.net/content/reference-annotations"
    st.write(
        "Using Beatles chord data gathered by [Christopher Harte](%s) for his 2010 PhD thesis, a Markov model is created containing probabilities of transitioning from one chord to the next. Choose from any Beatles song below to generate new chord sequences reminiscent of the original."
        % harte_url
    )

    colA, colB = st.columns(2)
    with colA:
        st.video("https://www.youtube.com/watch?v=mwBdWVTR-o8")
        st.video("https://www.youtube.com/watch?v=YBcdt6DsLQA")

    with colB:
        st.video("https://www.youtube.com/watch?v=e9vUCdfwlgw")
        st.video("https://www.youtube.com/watch?v=9BznFjbcBVs")

    # list albums and their songs
    chord_lab_data_path = r"./data/beatles-annotations/chordlab/The Beatles"
    seg_lab_data_path = r"./data/beatles-annotations/seglab/The Beatles"
    albums = [name for name in os.listdir(chord_lab_data_path) if os.path.isdir(os.path.join(chord_lab_data_path, name))]
    albums.sort()
    pretty_albums = [album.replace("_", " ") for album in albums]
    prettier_albums = [album.split("-")[1] for album in pretty_albums]

    st.subheader("Beatles Chord Generator")
    st.write(
        "Pick a song to generate its chord transition matrix. Choose how long you'd like the generated output to be, whether to initialize with the original chord from the song, and to generate results per section."
    )

    col1, col2 = st.columns(2)
    with col1:
        album_selection = st.selectbox("Album:", (prettier_albums))

    with col2:
        idx = prettier_albums.index(album_selection)
        album_path = chord_lab_data_path + "/" + albums[idx]
        songs = []

        for file in os.listdir(album_path):
            if file.endswith(".lab"):
                songs.append(file)

        songs.sort()
        pretty_songs = [song.replace("_", " ") for song in songs]
        prettier_songs = [song.split("-")[-1] for song in pretty_songs]
        prettiest_songs = [song.split(".lab")[0] for song in prettier_songs]

        song_selection = st.selectbox("Song:", (prettiest_songs))

    col3, col4 = st.columns(2)

    with col3:
        segment_output = st.checkbox("Segment by verse/chorus etc.")
        initial_chord = st.checkbox("Initialize with random chord")

    with col4:
        segment_length = st.text_input("Output sequence length:", value="8")

    if st.button("Generate"):
        song_idx = prettiest_songs.index(song_selection)
        album_idx = prettier_albums.index(album_selection)
        song_path = (
            chord_lab_data_path + "/" + albums[album_idx] + "/" + songs[song_idx]
        )

        if segment_output:
            segment_path = (
                seg_lab_data_path + "/" + albums[album_idx] + "/" + songs[song_idx]
            )
            original_order = get_original_order_of_sections(segment_path)
            original_chord_progression = get_original_chord_progression(song_path)

            st.subheader("Original ordering of sections")
            ss = ""
            for section in original_order:
                ss += section + ", "

            # drop last two chars
            ss = ss[:-2]
            st.write(ss)

            st.subheader("Original chord progression")
            ss = ""
            for chord in original_chord_progression:
                ss += chord + ", "

            ss = ss[:-2]
            st.write(ss)

            (
                outputs,
                chord_labs,
                section_labels,
                dict_of_tm,
                tm_names,
            ) = generate_segment_sequences(
                song_path, segment_path, int(segment_length), initial_chord
            )

            k = 0
            for section in section_labels:
                st.header(section.upper())
                st.subheader(
                    "Transition matrix: " + song_selection + " (" + section + ")"
                )
                st.write(dict_of_tm[tm_names[k]])
                col5, col6 = st.columns(2)
                with col5:
                    st.subheader("State space of chords")
                    st.write(chord_labs[k])
                with col6:
                    st.subheader("Generated chord sequence")
                    st.write(outputs[k])
                k = k + 1

        else:
            original_chord_progression = get_original_chord_progression(song_path)
            st.subheader("Original chord progression")
            ss = ""
            for chord in original_chord_progression:
                ss += chord + ", "

            ss = ss[:-2]
            st.write(ss)

            output, state_space, transition_matrix = generate_sequence(
                song_path, int(segment_length), initial_chord
            )

            st.subheader("Transition matrix: " + song_selection)
            st.write(transition_matrix)
            col5, col6 = st.columns(2)
            with col5:
                st.subheader("State space of chords")
                st.write(state_space)
            with col6:
                st.subheader("Generated chord sequence")
                st.write(output)


if __name__ == "__main__":
    app()
