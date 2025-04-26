import streamlit as st
import pandas as pd
import json
import math

# --- Configuration ---
SONGLIST_FILE = 'songs.json' # Expects the JSON file in the same directory

# --- Helper Functions ---
def format_songlength(milliseconds):
    """Converts milliseconds to a MM:SS formatted string."""
    if milliseconds is None or not isinstance(milliseconds, (int, float)) or milliseconds < 0:
        return "N/A"
    try:
        # Ensure milliseconds is treated as a number before division
        total_seconds = int(float(milliseconds) / 1000)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02}:{seconds:02}"
    except (ValueError, TypeError):
         return "Invalid" # Handle cases where conversion to float fails
    except Exception:
        return "Error"

@st.cache_data # Cache the data loading to improve performance
def load_song_data(file_path):
    """Loads song data from the specified JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Ensure data is a list of dictionaries
        if not isinstance(data, list):
            st.error(f"Error: Expected a JSON list (array) in {file_path}, but found {type(data)}.")
            return None
        if not all(isinstance(item, dict) for item in data):
             st.warning(f"Warning: Some items in {file_path} are not dictionaries (songs). Skipping non-dictionary items.")
             data = [item for item in data if isinstance(item, dict)]

        df = pd.DataFrame(data)

        # Ensure required columns exist, fill with None if missing
        # Use lowercase 'songlength' consistent with previous code
        required_cols = ['Name', 'Artist', 'Playlist', 'Year', 'songlength']
        missing_cols = []
        for col in required_cols:
            # Check for case-insensitivity in column names if needed, but stick to exact match for now
            if col not in df.columns:
                 # Attempt to find case-insensitive match (optional, can be complex)
                found_match = False
                for existing_col in df.columns:
                    if existing_col.lower() == col.lower():
                        st.warning(f"Info: Renaming column '{existing_col}' to '{col}' for consistency.")
                        df.rename(columns={existing_col: col}, inplace=True)
                        found_match = True
                        break
                if not found_match:
                    df[col] = None # Add missing column
                    missing_cols.append(col)

        if missing_cols:
             st.warning(f"Warning: Column(s) {missing_cols} not found in {file_path}. They will be shown as empty.")

        # --- Process Playlist column ---
        # Check if 'Playlist' column exists and is not entirely null before processing
        if 'Playlist' in df.columns and df['Playlist'].notna().any():
             # Ensure the column is string type before using .str accessor
            df['Playlist'] = df['Playlist'].astype(str).str.split('\\').str[0]
            # Handle potential NaNs introduced if original was NaN
            df['Playlist'] = df['Playlist'].replace('nan', None) # Replace string 'nan' if created
        elif 'Playlist' not in df.columns:
             st.warning("Playlist column not found, cannot process or filter by playlist.")
             df['Playlist'] = None # Ensure column exists if missing entirely

        #Filter out only songs from the specific game
        df = df[df["Playlist"] == "guitar hero 3"]

        return df

    except FileNotFoundError:
        st.error(f"Error: Song list file '{file_path}' not found.")
        st.info(f"Please make sure '{file_path}' is in the same directory as the script and contains your song list in JSON format.")
        return None
    except json.JSONDecodeError:
        st.error(f"Error: Could not decode JSON from '{file_path}'. Please ensure it's a valid JSON file.")
        st.info("The file should start with '[' and end with ']', with song objects '{...}' separated by commas.")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred while loading the data: {e}")
        return None

# --- Streamlit App Layout ---
# Use centered layout (default) for better mobile experience
st.set_page_config(page_title="Clone Hero Song Browser")

st.title("🎸 Clone Hero Song Browser")

# Load Data
df_songs = load_song_data(SONGLIST_FILE)

if df_songs is not None and not df_songs.empty:
    st.write(f"Loaded **{len(df_songs)}** songs.")

    # --- Filtering Controls ---
    # Place filters in the main area instead of sidebar
    st.subheader("Filter Songs")

    # Use columns for better layout on wider screens, stacks vertically on mobile
    col1, col2 = st.columns([1,1]) # Adjust ratios if needed

    with col1:
        search_name = st.text_input("Filter by Song Name", key="search_name")

    with col2:
        search_artist = st.text_input("Filter by Artist", key="search_artist")


    st.divider() # Visual separator

    # --- Apply Filters ---
    filtered_df = df_songs.copy() # Start with all songs

    # Apply text filters (case-insensitive)
    if search_name:
        # Check if 'Name' column exists
        if 'Name' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Name'].astype(str).str.contains(search_name, case=False, na=False)]
        else:
            st.warning("Cannot filter by Name: 'Name' column missing.")

    if search_artist:
         # Check if 'Artist' column exists
        if 'Artist' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Artist'].astype(str).str.contains(search_artist, case=False, na=False)]
        else:
            st.warning("Cannot filter by Artist: 'Artist' column missing.")


    # --- Prepare Data for Display ---
    if not filtered_df.empty:
        # Format song length
        if 'songlength' in filtered_df.columns:
            # Apply formatting
            filtered_df['Length'] = filtered_df['songlength'].apply(format_songlength)
        else:
            filtered_df['Length'] = "N/A" # Handle missing column

        # Select and order columns for display
        # Ensure all columns exist before selection to avoid errors
        display_columns = []
        for col in ['Name', 'Artist', 'Length', 'Playlist', 'Year']:
             if col in filtered_df.columns:
                  display_columns.append(col)
             elif col == 'Length' and 'Length' in filtered_df.columns: # Special case for derived column
                  display_columns.append('Length')


        display_df = filtered_df[display_columns]

        # Rename Length column for clarity in display if it exists
        if 'Length' in display_df.columns:
             display_df = display_df.rename(columns={'Length': 'Song Length (MM:SS)'})

        # --- Display Table ---
        st.write(f"### Filtered Song List ({len(display_df)} results)")
        st.dataframe(
            display_df,
            hide_index=True,
            use_container_width=True # Adapts table width to container
            )
    else:
        st.warning("No songs match your current filter criteria.")

elif df_songs is not None and df_songs.empty:
    st.warning(f"The file '{SONGLIST_FILE}' was loaded but appears to be empty or contains no valid song entries.")
else:
    # Error messages are shown by load_song_data()
    st.stop() # Stop execution if data loading failed