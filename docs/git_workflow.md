# Git Workflow

## Branch Structure
The following is how our branches are structured for this project.

### Main Branch
The main branch will do the following:
- Have the latest integrated version of the project
- Kept stable
- No direct commits allowed
 

### Individual Branch(es)
The individual branches named after each team member will do the following:
- All dev work is done in your named branch
- No one will commit directly to main
- Merge into main only through PR

### Daily Workflow
After cloning the repo, to access your branch you will do the following:
- Click the branch icon in your IDE
- If it does not exist yet under local...
  - Click your branch under "remote"
  - Hit the "checkout" button, and now you should be working in your branch.  

Before starting any sprint work, we need to ensure we keep our branches up to date to prevent conflicts later on:
- Switch to the main branch
- Pull the latest changes via GUI or via command "git pull origin main"
- Swap back to your branch
- Merge main into your individual branch via GUI or via command "git merge main"

### Merge Process
When you finish a feature/task:
- Push to your individual branch
- Open a PR for your-branch-name -> main
- Get approval from 1 teammate (pref. someone working on the same general project part)