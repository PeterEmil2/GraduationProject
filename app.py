from flask import Flask,render_template,redirect,url_for,request,flash,session, send_file
from database import *
from BackendClasses.Similarity import Similarity
from BackendClasses.TextExtraction import *
from io import BytesIO
import hashlib
import pyotp

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Amir Secret key'
@app.route('/signup',methods=['GET','POST'])
def signUp():
    if request.method=='GET':
        return render_template('signUp.html')
    else:
        name=request.form['name']
        email=request.form['email']
        password=request.form['password']
        confirmationPassword=request.form['confirmPassword']
        company_name=request.form['companyName']
        if(password!=confirmationPassword):
             flash("Password doesn't match!!! ")
        else:
            password = hashlib.sha256(password.encode('utf-8')).hexdigest()
            signUpRegistration(name,email,password,company_name)
       
        return redirect(url_for('signin'))
       
@app.route('/')
def home():
    if 'ID' in session:
        result = getHrJobOpportunity(session['ID'])
        return render_template('hrHomee.html',Data = result)
    return render_template('Getstarted.html')

@app.route('/signIn',methods=['GET','POST'])
def signin():
    if (request.method=='GET'):
       return render_template('signin.html')
    else:   
        email = request.form['email']
        password = request.form['password']
        password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        id=authenticate(email=email,password=password)
        if id ==-1 :
            pass
        else:  
            session['Email']=email
            session['tid'] =id
            return redirect(url_for('totp'))
        
@app.route('/signin/2fa', methods = ['GET', 'POST'])
def totp():
    if 'tid' not in session:
        return redirect('/')
    if request.method == 'GET':
        otp = get_otp(session['tid'])
        if otp:
            return render_template('twofa.html', secret=None)
        otp = pyotp.random_base32()
        set_otp(session['tid'], otp)
        return render_template('twofa.html', secret=otp)
    token = get_otp(session['tid'])
    otp = int(request.form.get('otp'))
    if pyotp.TOTP(token).verify(otp):
        session['ID'] = session['tid']
        session.pop('tid')
        return redirect(url_for("home"))
    else:
        flash("You have supplied an invalid 2FA token!", "danger")
        return redirect(url_for("totp"))
  
@app.route('/aboutus')
def aboutus():
    return render_template('Aboutus.html')

@app.route('/FillForm/<int:ID>',methods=['GET','POST'])
def FillForm(ID):
    if (request.method=='GET'):
        return render_template('FillForm.html')
    else:   
        userName = request.form['Name']
        userEmail = request.form['Email']
        userEducation = request.form['Education']
        userSkills=request.form['Skills']
        userAddress = request.form['Address']
        userPhoneNumber = request.form['phoneNumber']
        userProjects=request.form['Projects']
        userExperience = request.form['Experience']
        
        userObjective = request.form['Objective']

        fillForm(userName,userEmail,userEducation,userSkills,userAddress,userPhoneNumber,userProjects,userExperience,ID,userObjective)
        return redirect(url_for('home'))
 
@app.route('/AddJobForm')
def AddJobForm():
    return render_template('AddJobForm.html')

@app.route('/BrowseJob')
def BrowseJob():
    return render_template('BrowseJob.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('signin'))

@app.route('/contactus')
def contactus():
    return render_template('contactus.html')

@app.route('/Getstarted')
def Getstarted():
    return render_template('Getstarted.html')

@app.route('/Uploadtype/<int:ID>')
def Uploadtype(ID):
    return render_template('Uploadtype.html',id = ID)

@app.route('/NotFound')
def NotFound():
    return render_template('Notfound.html')

@app.route('/addOpportunity',methods=['GET','POST'])
def addJob():
    if (request.method=='GET'):
       return render_template('AddJobForm.html')
    else:   
        jobName = request.form['jobName']
        jobDescription = request.form['jobDescription']
        imageSource=request.form['imageSource']
        if(jobName!="" and jobDescription!="" and imageSource!=""):
            addJobOpportunity(session['ID'],jobName,jobDescription,imageSource)
            return redirect(url_for('home'))

@app.route('/jobDetails/<int:ID>', methods=['GET', 'POST'])
def showJobDetails(ID):
    if request.method == 'GET':
        Details=getJobDetails(ID)
        Applicants=getApplicants(ID)
        active = get_active(ID)
        return render_template('jobDetails.html',details = Details,applicants=Applicants, active=active)
    Details=getJobDetails(ID)
    Applicants=getApplicantsByExp(ID, int(request.form['experience']))
    apps = []
    valid_designations = get_designition(Details[0]+'\t'+Details[1])
    print(valid_designations)
    def isApplicable(a_designation:list, j_designation:list)->bool:
        for i in a_designation:
            for j in j_designation:
                if i == j:
                    return True
        return False
    for i in Applicants:
        app_designation = i[-1].split(', ')
        if isApplicable(app_designation, valid_designations):
            apps.append(i)
    active = get_active(ID)
    return render_template('jobDetails.html',details = Details,applicants=apps, active=active)

@app.route('/deleteOppurtunity/<int:ID>')
def removeOppurtunity(ID):
    deleteJobOpportunity(ID)
    return redirect(url_for('home'))
    
@app.route('/get-best-applicants/<int:jobid>')
def process(jobid):
    if jobid in [i[2] for i in getHrJobOpportunity(session['ID'])] and get_active(jobid)==1:
        deactivate_job(jobid)
        data = getApplicants(jobid)
        applicants_id = [i[4] for i in data]
        similarity = Similarity([i[3] for i in data], getJobDetails(jobid)[1])
        save_similarity(applicants_id, similarity)
        return redirect(url_for('showJobDetails',ID=jobid))
    return redirect(url_for('showJobDetails',ID=jobid))

@app.route('/file/<int:file_id>')
def get_file(file_id: int):
    return send_file(
        BytesIO(get_file_by_id(file_id)),
        mimetype='application/pdf'
    )

@app.route('/upload-resume/<int:job_id>', methods=['GET','POST'])
def upload_resume(job_id : int ):
    if request.method == 'GET':
        return render_template('UploadCv.html')
    file = request.files['UploadFile']
    filename = file.filename
    file = file.read()
    resume_txt = extract_text(file)
    skills = get_skills(resume_txt)
    designation = get_designition(resume_txt)
    experience = get_years_of_exp(resume_txt)
    add_new_application(filename, file, ', '.join(skills), ', '.join(designation), experience, job_id)
    return redirect('/')