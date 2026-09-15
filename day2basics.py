print("===============================================================")
print ("job portal")
print("===============================================================")

name=input("Enter your name")
location=input("Enter your location")
Preferredjob=input("Enter your Preferredjob")
Minimumsalary=int(input("Enter your Minimumsalary"))
skill=input("Enter your skill")
jobtype=input("Enter your job type")


if Minimumsalary >12:
    print("accepted")
else:
    print("notvalid")