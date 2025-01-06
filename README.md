# https://gintarasdev.com/
Personal blog site build using HB Theme with Hugo.

Start site locally: `hogo server -D`
Build site: `hugo`


For deployment in AWS S3: after build step run `python .\update-urls.py`.
> This is needed because Hugo uses folder paths as paths to pages while the actual page contents are under `index.html` in those folders. This script tries to find all urls with folders and add `index.html` part to them so AWS S3 could understand what the site is trying to get. 
