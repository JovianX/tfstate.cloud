# Terraform state in the ☁️

The simplest way to securely store the Terraform **State** and **Locks** in the cloud.
No browser, no custom clients, and no cumbersome configuration required.
Works magically right from the `terminal`.

            
            curl https://get.tfstate.cloud
            




## 0. Instructions
Get the insturcitons in the terminal using `curl` command:
```bash
curl https://get.tfstate.cloud
```
Example output:
```bash

 ▛▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▜
 ▌ TFstate☁️ CLOUD ▐ Store Terraform State
 ▙▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▟   and Terraform Locks in the cloud.

- Create a new account and get the backend configuration (replace with your email and password):
curl https://get.tfstate.cloud -F email=my@email.com -F password=MyPassword -F action=create

- Retrieve the backend configuration (default: -F action=get):
curl https://get.tfstate.cloud -F email=my@email.com -F password=MyPassword


- Run `terraform init` and `terraform apply` after `backend.tf` backend configuration file is created.
```
## 1. Register
Register to the service using your email and password, on registration tfstate.cloud will generate  `account_id` and `account_secret` for the backend configuration:

```bash
curl https://get.tfstate.cloud -F action=create -F email=<my@email.com> -F password=<MyPassword>
```
Example output:
```bash
#
# Terraform state managed at https://tfstate.cloud
# Save to file `backend.tf` in your terraform configuration directory.
#
# Account_ID=<account_id>
# Account_Secret=<account_secret>
#
terraform {
backend "http" {
    username       = "<account_id>"
    password       = "<account_secret>"
    address        = "https://get.tfstate.cloud/terraform_state/space1"
    lock_address   = "https://get.tfstate.cloud/terraform_lock/space1"
    unlock_address = "https://get.tfstate.cloud/terraform_lock/space1"
    lock_method    = "PUT"
    unlock_method  = "DELETE"
    }
}
```
## 2. Configure backend
Save the configuration output as `backend.tf` in the  terraform configuration directory:

```bash
curl https://get.tfstate.cloud -F email=<my@email.com> -F password=<MyPassword> | tee backend.tf
```

```bash
terraform-project/
├── backend.tf   # <--------<<
├── main.tf
├── output.tf
├── providers.tf
└── ...
```
```bash
$ cat backend.tf
#
# Terraform state managed at https://tfstate.cloud
# Save to file `backend.tf` in your terraform configuration directory.
#
# Account_ID=<account_id>
# Account_Secret=<account_secret>
#
terraform {
backend "http" {
    username       = "<account_id>"
    password       = "<account_secret>"
    address        = "https://get.tfstate.cloud/terraform_state/space1"
    lock_address   = "https://get.tfstate.cloud/terraform_lock/space1"
    unlock_address = "https://get.tfstate.cloud/terraform_lock/space1"
    lock_method    = "PUT"
    unlock_method  = "DELETE"
    }
}
```
## 3. Initialize Terraform
```bash
$ terraform init

Initializing the backend...

Successfully configured the backend "http"! Terraform will automatically
use this backend unless the backend configuration changes.
GET https://get.tfstate.cloud/terraform_state/space1

Initializing provider plugins...

...

Terraform has created a lock file .terraform.lock.hcl to record the provider
selections it made above. Include this file in your version control repository
so that Terraform can guarantee to make the same selections by default when
you run "terraform init" in the future.

Terraform has been successfully initialized!

You may now begin working with Terraform. Try running "terraform plan" to see
any changes that are required for your infrastructure. All Terraform commands
should now work.
```
