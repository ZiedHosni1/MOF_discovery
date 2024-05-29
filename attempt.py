import csv
import pickle


# Step 1: Read the CSV file
def read_csv_file(csv_file_path):
    data = []
    with open(csv_file_path, 'r') as csvfile:
        csvreader = csv.DictReader(csvfile)
        for row in csvreader:
            data.append(row)
    return data


# Step 2: Process the data (if needed)
# This step can include data cleaning, manipulation, etc.

# Step 3: Serialize the data and save to a pickle file
def save_as_pickle(data, pickle_file_path):
    with open(pickle_file_path, 'wb') as picklefile:
        pickle.dump(data, picklefile)


# Example usage
if __name__ == "__main__":
    csv_file_path = 'C:\Users\juice\PycharmProjects\MOF_discovery\mof_properties.csv'  # Path to your CSV file
    pickle_file_path = 'C:\Users\juice\PycharmProjects\MOF_discovery'  # Path where the pickle file will be saved

    # Step 1: Read CSV file
    data = read_csv_file(csv_file_path)

    # Step 2: Process data (if needed)
    # For example, convert data types, filter data, etc.

    # Step 3: Save data as a pickle file
    save_as_pickle(data, pickle_file_path)
