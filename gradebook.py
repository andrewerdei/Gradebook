from pathlib import Path
import pandas as pd
import numpy as np

here = Path(__file__).parent    #Current executing file
data_folder = here / "data"     #Folder where data is stored

#first load and clean data
#load roster data
roster = pd.read_csv(
    data_folder / "roster.csv",
    converters = {"NetID": str.lower, "Email Address": str.lower},     #Will help simplify string comparisons
    usecols = ["Section", "Email Address", "NetID"],
    index_col = "NetID",
)

#load hw and exam data
hw_exam_grades = pd.read_csv(
    data_folder / "hw_exam_grades.csv",
    converters = {"SID": str.lower},
    usecols = lambda x: "Submission" not in x,  #If "Submission" is in the column name, then column wont be included
    index_col= "SID",
)

#load quiz data
quiz_grades = pd.DataFrame()
for file_path in data_folder.glob("quiz_*_grades.csv"):         #Find all CSV files and load them with pandas
    quiz_name = " ".join(file_path.stem.title().split("_")[:2])
    quiz = pd.read_csv(
        file_path,
        converters = {"Email": str.lower},
        index_col = ["Email"],
        usecols = ["Email", "Grade"],
    ).rename(columns = {"Grade": quiz_name})
    quiz_grades = pd.concat([quiz_grades, quiz], axis=1)        #axis=1 Adds each new quiz into new column rather than row in DataFrame

#Merge roster and hw grades
final_data = pd.merge(roster, hw_exam_grades, left_index=True, right_index=True,)
#Merge quiz grades
final_data = pd.merge(final_data, quiz_grades, left_on="Email Address", right_index=True)
final_data = final_data.fillna(0)   #Fill any nan values as 0s


#Calculate exam total score
n_exams = 3
for n in range(1, n_exams + 1):
    final_data[f"Exam {n} Score"] = (final_data[f"Exam {n}"] / final_data[f"Exam {n} - Max Points"])

#Calculate hw scores
homework_scores = final_data.filter(regex=r"^Homework \d\d?$", axis=1)
homework_max_points = final_data.filter(regex=r"^Homework \d\d? -", axis=1)
sum_of_hw_scores = homework_scores.sum(axis=1)
sum_of_hw_max = homework_max_points.sum(axis=1)
final_data["Total Homework"] = sum_of_hw_scores / sum_of_hw_max
#rename columns names to match each other so panda can perform operations on matching labels
hw_max_renamed = homework_max_points.set_axis(homework_scores.columns, axis=1)
average_hw_scores = (homework_scores / hw_max_renamed).sum(axis=1)
final_data["Average Homework"] = average_hw_scores / homework_scores.shape[1]   #divide average scores by number of assignments
final_data["Homework Score"] = final_data[["Total Homework", "Average Homework"]].max(axis=1)

#Calculate quiz scores
quiz_scores = final_data.filter(regex=r"^Quiz \d$", axis=1)
quiz_max_points = pd.Series({"Quiz 1": 11, "Quiz 2": 15, "Quiz 3": 17, "Quiz 4": 14, "Quiz 5": 12})
sum_of_quiz_scores = quiz_scores.sum(axis=1)
sum_of_quiz_max = quiz_max_points.sum()
final_data["Total Quizzes"] = sum_of_quiz_scores / sum_of_quiz_max
average_quiz_scores = (quiz_scores / quiz_max_points).sum(axis=1)
final_data["Average Quizzes"] = average_quiz_scores / quiz_scores.shape[1]
final_data["Quiz Score"] = final_data[["Total Quizzes", "Average Quizzes"]].max(axis=1)


#Calculate the letter grade
weightings = pd.Series({
    "Exam 1 Score": 0.05,
    "Exam 2 Score": 0.1,
    "Exam 3 Score": 0.15,
    "Quiz Score": 0.30,
    "Homework Score": 0.4,
})

final_data["Final Score"] = (final_data[weightings.index] * weightings).sum(axis=1)
final_data["Ceiling Score"] = np.ceil(final_data["Final Score"] * 100)              #ceil to round each grade up to the nearest integer

grades = {
    90: "A",
    80: "B",
    70: "C",
    60: "D",
    0: "F",
}

def grade_mapping(value):               #only works properly when grades arranged in descending order
    for key, letter in grades.items():
        if value >= key:
            return letter
        
letter_grades = final_data["Ceiling Score"].map(grade_mapping)
final_data["Final Grade"] = pd.Categorical(letter_grades, categories=grades.values(), ordered=True) #create categorical column after mapping letters to grades

#Group Data
for section, table in final_data.groupby("Section"):
    section_file = data_folder / f"Section {section} Grades.csv"
    num_students = table.shape[0]
    print(f"In Section {section} there are {num_students} students saved to " f"file {section_file}.")
    table.sort_values(by=["Last Name", "First Name"]).to_csv(section_file)

print(final_data)

