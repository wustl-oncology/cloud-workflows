# Getting set up on Google Cloud

### Setting up a billing account

The WUSTL IT department controls access through WUSTL accounts, so unless you'd like to open an Google Cloud Platform (GCP) account with your personal credit card, the first thing you have to do is contact them.  Their [Google Cloud](https://it.wustl.edu/services/cloud-computing/google-cloud-platform/) page contains links to "Request a new WashU Google Cloud Project".

At the current time, our GCP costs go through a middleman/reseller called the Burwood group. You'll need to generate a purchase order to them with some reasonable amount of funding on it before they can activate it. 

Once that's in place, IT hands you the keys to the castle.

### Administering your account

At this point you're pretty much on your own, which can be a little bit overwhelming, as GCP offers hundreds of different features, mostly accessible through your [Cloud Console](https://console.cloud.google.com/).  Some of the information in the [cloud-workflows repository](https://github.com/wustl-oncology/cloud-workflows/blob/main/docs/gcloud_setup.md) is likely to be helpful, and can guide you in assigning permissions, setting up projects, and using the command line interface to push and pull data. 

### Monitoring costs

One of the best things about cloud computing is that you have access to essentially unlimited resources.  One of the worst things about it is that providers will happily charge you essentially unlimited dollars if you use them.  It's key to understand costs and to monitor them carefully.  The "Billing" tab of the cloud console offers lots of information on this, and it is a good idea to [set up billing alerts](https://www.the-swamp.info/blog/setting-budget-alerts-gcp-billing-account/) so that you can intercept and shut down rogue processes before getting a painful surprise. The [full documentation for billing](https://cloud.google.com/billing/docs/how-to/budgets) may be useful as well, as will [the GCP pricing calculator](https://cloud.google.com/products/calculator).  Keep in mind that there are discounts provided through Burwood that will help ameliorate those costs, and you should contact IT for the latest on what those are, as they may change over time.

