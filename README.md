# Simplilearn study agent

This agent checks your Python class and looks up Simplilearn pages for changes.

Your current class is the free [Python course with certificate](https://www.simplilearn.com/learn-python-basics-free-course-skillup). It starts from zero and goes through NumPy, Pandas, Matplotlib, and Scikit-Learn. The agent also watches three later programs, and it does not mark you enrolled in them:

- [Python Certification Course](https://www.simplilearn.com/mobile-and-software-development/python-development-training)
- [Data Science with Python](https://www.simplilearn.com/big-data-and-analytics/python-for-data-science-training)
- [Applied Agentic AI](https://www.simplilearn.com/agentic-ai-course-training)

## Check progress and search for updates

```bash
python3 -m study_agent
```

The agent reads `data/progress.json`, opens each page in `data/profile.json`, and compares the page with the last copy it saved. The report names the next lesson, gives one short practice, and lists what changed.

To review the lesson log without opening the web:

```bash
python3 -m study_agent offline
```

## Mark a lesson done

After you finish lesson 1:

```bash
python3 -m study_agent done 1
```

To undo that:

```bash
python3 -m study_agent undo 1
```

To save a note about what you studied:

```bash
python3 -m study_agent note Finished the print exercise
```

## If your class is different

Edit `data/profile.json`. Set `"enrolled": true` on a bootcamp you are actually taking. The checklist in `data/curriculum.json` matches the free Python course. If you are in a different Python course, say so and the checklist can be switched.
