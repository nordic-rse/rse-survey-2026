"""Fixtures that are used throughout the rse-survey-report."""

# the countries of each country group
COUNTRY_GROUPS = {
    "Nordics": ["Finland", "Norway", "Sweden", "Denmark", "Iceland", "Estonia"],
    "Germany": ["Germany"],
    "Netherlands": ["Netherlands"],
}

# the group of the chapter analyses; a key of COUNTRY_GROUPS
TARGET = "Nordics"

# the groups to compare the target with, in the "Between countries" section
COMPARE = ["Germany", "Netherlands"]

# the countries of the target group
TARGET_COUNTRIES = COUNTRY_GROUPS[TARGET]

# answer scales, as likert5_levels() and likert_time_levels() in rse-book
AGREEMENT_LEVELS = [
    "Strongly disagree",
    "Disagree",
    "Neither agree or disagree",
    "Agree",
    "Strongly Agree",
]
LIKERT_LEVELS = ["0% (None at all)", "20%", "40%", "60%", "80%", "100% (All my time)"]

# age groups from socio3_0, as assign_age_groups_two() in rse-book
AGE_GROUPS = {
    "18 to 24 years": "Below 35",
    "25 to 34 years": "Below 35",
    "35 to 44 years": "35-45",
    "45 to 54 years": "45+",
    "55 to 64 years": "45+",
    "Age 65 or older": "45+",
}

# categories and their question ids [categories are handcoded]
CATEGORIES = {
    "Setup": ["startlanguage", "startdate"],
    "RSE role": ["rse1", "rse3", "rse4de"],
    "Education": ["edu2", "edu1"],
    "Software experience": ["soft2can", "soft1can"],
    "Open science": ["open1de", "open1can"],
    "UK RSE network": ["ukrse1", "ukrse3"],
    "RSE Organisation": [
        "org1can",
        "org1cz",
        "org1swiss",
        "org2can",
        "org3nord",
        "org3us",
        "org4nord",
        "org4us",
        "org5us",
        "org3de",
        "org4de",
        "org5de",
        "org6de",
        "org7de",
    ],
    "Employment": [
        "currentEmp1",
        "currentEmp1qde",
        "currentEmp1qswiss",
        "currentEmp1nl",
        "currentEmp1qzaf",
        "prevEmp1",
        "prevEmp1qde",
        "prevEmp1nl",
        "prevEmp1qswiss",
        "currentEmp5",
        "currentEmp6",
        "currentEmp60",
        "currentEmp12",
        "currentEmp10",
        "currentEmp11",
        "currentEmp11qcl",
        "currentEmp11qzaf",
        "currentEmp13",
        "currentEmp2q",
        "currentEmp20deqde",
        "currentEmp20qus",
        "currentEmp21deqde",
        "currentEmp22deqde",
        "currentEmp23deqde",
        "currentEmp24deqde",
    ],
    "Likert scales": [
        "likert0",
        "likert1",
        "likert2a",
        "likert2b",
        "likert3a",
        "likert3b",
        "likert4a",
        "likert4b",
        "likert4c",
        "likert5b",
        "likert5a",
    ],
    "Turnover": ["turnOver3", "turnOver3zaf", "turnOver4zaf"],
    "Work activities": [
        "currentWork1",
        "currentWork2",
        "currentWork2qcl",
        "currentWork3nord",
    ],
    "Publications": ["paper3mod", "paper2mod", "ref1uk"],
    "Conferences": ["conf1can", "conf2can", "ukrse12sa"],
    "Project Management": [
        "proj1can",
        "proj4can",
        "proj5can",
        "proj5zaf",
        "proj6zaf",
        "proj6uk",
        "proj7can",
        "proj8can",
    ],
    "Job stability": ["stability1", "stability2"],
    "Training": [
        "train2",
        "train3",
        "train4",
        "train4qzaf",
        "train5",
        "skillNord",
        "skill2",
    ],
    "Funding": ["fund1nord", "fund1can", "fund1uk", "fund3", "fund3qnl"],
    "Tooling": ["tool2", "tool4can", "tool5", "tool5can"],
    "Generative AI": ["genAI1", "genAI2", "genAI3", "genAI4", "genAI5", "genAI6"],
    "Demographics": ["socio3"],
}
