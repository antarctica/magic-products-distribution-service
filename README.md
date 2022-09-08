# MAGIC Products Distribution

Service for distributing products produced or managed by the Mapping and Geographic Information Centre (MAGIC) at the
British Antarctic Survey (BAS).

## Overview

### Purpose

This service is intended to allow MAGIC to securely distribute products with relevant end-users.

Specifically, this service acts as a data access system, to allow links within items in the Data Catalogue (a data
discovery system) that describe products, to be downloaded if they have access.

### Status

This project is an alpha Minimal Viable Product (MVP) working towards a beta MVP. This means:

* this service may stop working at any time
* this service may not work as expectedly (but not destructively)
* this service may change at any time (in terms of implementation not functionally)
* use-cases supported by this service are limited and restrictive
* documentation may be out of date
* limited support is provided

### Limitations

This service has a number of limitations, including:

- products cannot use conditional access, such as agreeing to a licence before use
- products cannot be unrestricted, an alternative data access system needs to be used
- products cannot use multiple, independent, sets of access conditions for different sets of people - such as externals
- where access is restricted to a set of users, they cannot be identified using email addresses, which are easier
- where access is restricted to users or groups, these users and groups must be within the NERC Active Directory
- files to be deposited in this service must be located on the same computer used to run the tool for this service
- there is only a single, production, environment available, there is no training environment for example
- a product's artefact's constraints will not change once deposited, even if the product/resource constraint changes

See the project [issue tracker](#issue-tracking) for planned features that may address these limitations.

### Scope

#### Products

This service SHOULD be used for distributing products created or managed by MAGIC. This service MUST NOT be used for
distributing any datasets (regardless of whether they are restricted or not).

For the purposes of this service, examples of things that would be considered a *product* includes:

* maps (typically with PDF and image outputs)
* annotated images

For the purposes of this service, examples of things that would be considered a *dataset* includes:

* DEMs
* point clouds, 3D meshes and related resources
* satellite imagery
* aerial photography and RPAS imagery

**Note:** These examples are not exhaustive, and it is accepted these definitions are imperfect and subjective.
Specific use-cases can be discussed as needed (using the *#data* channel in Slack initially).

Products and datasets are treated differently for practical and organisational reasons (e.g. storage size and the
number of items, and that in BAS, datasets are managed by the Polar Data Centre).

#### Access only

This service is a data access system, to allow authorised end-users to access, and download copies of, Artefacts
(files) deposited by a set of depositors (MAGIC staff). This service does not support end-users depositing products
themselves.

#### File sizes

As soft limits:

* the total size of Artefacts for each product/Resource SHOULD NOT exceed 3GB (giving roughly 8,500 deposits)

**Note:** It is fine for some products to exceed this limit, as its assumed most products will be significantly smaller
than this limit.

As hard limits, the
[SharePoint service limits](https://docs.microsoft.com/en-us/office365/servicedescriptions/sharepoint-online-service-description/sharepoint-online-limits)
apply. Namely:

* any file MUST NOT exceed 250GB
* the total, maximum, size of all files MUST NOT exceed 25TB
* the maximum number of items (files/folders) MUST NOT exceed 30 million

## Requirements

In addition to being within the [Scope](#scope) of this service, Resources (products) MUST meet these requirements
to be supported by this service:

**Note:** This service supports a limited set of use-cases.

1. the Resource must be considered a product within the [definition](#products) used by this service
2. the Resource (product) to be deposited MUST be described by a suitably complete metadata record [1], deposited in
   the ADD Metadata Toolbox catalogue (BAS Data Catalogue)
3. the Artefacts (files) that make up the Resource (product) MUST fit within the [soft file size limits](#file-sizes)

[1] Required resource metadata:

- a `file_identifier` property with a UUIDv4 value
- a `hierarchy_level` property with a value of 'product'
- at least, and no more than, one resource `constraint`, that must be the first of any constraints listed, with:
  - a `type` property with a value of 'access'
  - a `restriction_code` property with a value of 'restricted'
  - a `permissions` property with a list, with a single item, which is an object with:
    - a `scheme` property with a value of 'ms_graph'
    - a `scheme_version` property with a value of '1'
    - a `directory_id` property with a value of 'b311db95-32ad-438f-a101-7ba061712a4e'
    - either:
      - an `alias` property with a list of values that must be one of:
        - '~nerc' (where a product should be restricted to any NERC AAD principle)
      - an `object_id` property with a list of of values that must be:
        - an object identifier of a user or group object within the NERC AAD
- at least one resource `distribution` with:
  - a distributor of MAGIC
  - a `transfer_option` with:
    - a `href` value containing:
      - a URI using the `file://` protocol, referencing a locally accessible file, under 5GB in size

To clarify the requirements for resource constraints:

1. there MUST be one (and only one) resource access constraint that contains a permissions property
2. this access constraint with a permissions property, MUST be the first item in the list of resource constraints
3. multiple other resource constraints (of any type and form) may exist, providing these don't break (1) and (2) above

## Usage

### Test script

A test script is available to demonstrate an end-to-end process for depositing Artefacts within a Resource. It 
implements the [Workflow](#workflow) for this project, with the following exceptions:

* records aren't selected or read from the BAS Data Catalogue, a very simplified mock is used instead
* as a consequence, updated records aren't written back to the Data Catalogue, but output as local files

This test script combines and replaces the [older test scripts](#old-test-scripts) that tested specific parts of the 
workflow.

```shell
$ poetry run python test-chain.py
```

With no arguments, this command will list available commands.

The `sign-in` command authenticates a user or service principle for interacting with the Microsoft Graph API. It 
supports two OAuth flows (`device` for interactive use, `credentidals` for non-interactive), specified as a positional 
parameter. If using the `credentials` flow, create an `./auth-credentials` file [1].

Specifying the `deposit` command with no arguments will list available records for deposit. To deposit a resource 
with a file identifier:

```shell
$ poetry run python test-chain.py sign-in device
$ poetry run python test-chain.py deposit foo
```

Once deposited, a record can be withdrawn (reset) manually by:

* discarding changes to modified files within the catalogue mock using [git](https://stackoverflow.com/a/692329)
* removing the directory for the Resource from SharePoint

**Note:** You need suitable permissions to run this script:

* you need to be a member of the MAGIC Microsoft Office365 Team
* you need to have access access to an AWS IAM principle with the 
  `BAS-ADD-Catalogue-Downloads-Proxy-Function-Write-Staging` IAM customer managed policy attached

**Note:** This test script is not representative of how code for this service will be written.

[1] Example `auth-credentials.json`:

```json
{
  "username": "foo@bas.ac.uk",
  "password": "xxx"
}
```

### Old test scripts

#### Test upload script

A test script is available to check test files can be uploaded and permissions are set correctly etc. This script can be
ran within a [Development Environment](#development-environment).

```shell
$ poetry run python test-upload.py
```

**Note:** You need suitable permissions (being a member of MAGIC) to perform these instructions.

**Note:** You will be asked to sign in to the 'MAGIC-PDC Data Workflows PoC' application when running this script.

**Note:** This test script is not representative of how code for this service will be written.

#### Test lookup items script

A test script is available to check artefact lookup entries can be added programmatically to the Data Catalogue 
Downloads Proxy. This script can be ran within a [Development Environment](#development-environment).

```shell
$ poetry run python test-lookup.py
```

**Note:** You need suitable permissions (the `BAS-ADD-Catalogue-Downloads-Proxy-Function-Write-Staging` IAM customer 
managed policy attached to a suitable user within the BAS AWS account) to run this script.

**Note:** You need to setup AWS credentials to run this script, for example by running `aws configure` with the AWS CLI
installed.

**Note:** This test script is not representative of how code for this service will be written.

#### Test metadata record loading script

A test script is available to check an ISO 19115 metadata record using the BAS Metadata Library JSON encoding can be 
loaded and validated against it's default schema, and the schema specific to this service, which ensures it complies 
with the service [Requirements](#requirements). This script can be ran within a 
[Development Environment](#development-environment).

```shell
$ poetry run python test-record.py
```

**Note:** This test script is not representative of how code for this service will be written.

### Manually depositing Artefacts

**Note:** These instructions should only be used as a last resort, where automated methods have failed and the need is
urgent.

**Note:** You need suitable permissions (being a member of MAGIC) to perform these instructions.

To manually deposit Artefacts (files) for a Resource (product) that meets the [Requirements](#requirements):

1. export the metadata record for the Resource (product) from the Data Catalogue
2. from the [MAGIC Products Distribution](https://nercacuk.sharepoint.com/sites/MAGICProductsDistribution/_layouts/15/viewlsts.aspx?view=14)
   SharePoint site, select the relevant document library (use 'Main' if unsure)
3. click *+ New* -> *Folder* from the toolbar:
    * name the folder after the `file_identifier` property from the metadata record for the Resource
4. click *Edit in grid view* from the toolbar:
    * set the 'record_id' value for the new folder to the value of the `file_identifier` property in the metadata
      record for the Resource
    * set the 'artefact_id' value for the new folder to '-' (dash), as it doesn't apply
    * click *Exit grid view* from the toolbar
5. navigate into the newly created folder:
6. for each `distribution` listed in the metadata record for the Resource:
    1. upload the Artefact (file) listed in the `transfer_option.online_resource.href`, either using the *Upload*
       option in the toolbar, or by dragging & dropping into the main window
    2. click *Edit in grid view* from the toolbar:
        * set the 'resource_id' value for the uploaded file to the value of the `file_identifier` property in the
     metadata record for the Resource
        * set the 'artefact_id' value for the uploaded file to a new UUID value (using
     [this tool](https://www.uuidgenerator.net) for example)
        * click *Exit grid view* from the toolbar
7. for each `identification.constraint` listed in the metadata record for the Resource:
    1. if the constraint permissions uses an `permissions.alias` property, with a value of `~nerc`:
        1. select each file (Artefact) within the directory for the product (Resource):
        2. click *Share* from the toolbar
        3. click *People you specify can edit*
        4. change the selection to *People in NERC with the link*
        5. deselect the *Allow editing* option under Other settings
        6. click *Apply*
        7. from the 'Copy link' section, click *Copy* to view the sharing link for the file (Artefact)
        8. note this URL for use in creating Data Catalogue Download Proxy artefact lookup items
    2. if the constraint permissions uses an `permissions.object_id` property:
        1. for each object identifier:
            1. go to the [Azure Portal](https://portal.azure.com/) [1]
            2. enter the object identifier into the global search box from the top navigation
            3. either a group or user should be returned as a result (under an 'Azure Active Directory' heading) [2]
            4. select this group or user to view its details
            5. note the value for the 'Email' property for use in assigning permissions
            6. in SharePoint, select the directory for the product (Resource)
            7. click *Open the details pane* ('i' icon) from the toolbar
            8. from the 'Has access' section, click *Manage access*
            9. from the 'Direct access' section, click *Grant Access* ('+' icon)
            10. in the 'name' field, group or email field, enter the email address noted earlier
            11. click the 'who has access' link ('pencil' icon) and select the *Can View* option ('prohibited pencil'
                icon)
            12. do not enter a message
            13. deselect the 'Notify people' option
            14. click *Grant access*
        2. for each file (Artefact) within the directory for the product (Resource):
           1. note the URL for use in creating Data Catalogue Download Proxy artefact lookup items in the form of [3]
8. for each `distribution` listed in the metadata record for the Resource:
   1. create a
      [Data Catalogue Downloads Proxy artefact lookup item](https://gitlab.data.bas.ac.uk/MAGIC/add-metadata-toolbox#updating-downloads-proxy-artefacts-lookups)
      manually [4]
   2. update the `transfer_option.online_resource.href` value in the form of [5]
9. re-import the metadata record for the Resource (product) into the Data Catalogue

[1] Object identifiers cannot be specified when assigning permissions within the SharePoint UI. Therefore, object
identifiers need to be converted into a corresponding email address for the group or user each identifier identifies.
Users and groups can be searched for within the NERC Active Directory using the [Azure Portal](https://portal.azure.com).

[2] If no result is returned, contact support.

[3] `https://nercacuk.sharepoint.com/sites/MAGICProductsDistribution/Main/{resource_id}/{file_name}`

Where:

* `{resource_id}` is the value of the `file_identifier` property in the metadata
* `{file_name}` is the name of the file (URl encoded and including the file extension)

For example:

```
https://nercacuk.sharepoint.com/sites/MAGICProductsDistribution/Main/24dce09c-9eee-4d90-8402-63f63012d767/foo-map.pdf
```

[4]

```shell
# with the awscurl installed and access to a AWS IAM principle with appropriate privileges
$ awscurl --region eu-west-1 --service lambda --access_key $AWS_ACCESS_KEY_ID --secret_key $AWS_SECRET_ACCESS_KEY 'https://dvej4gdfa333uci4chyhkxj3wq0fkxrs.lambda-url.eu-west-1.on.aws/' --request POST --header 'Content-Type: application/json' --data $'{"origin_url": "{origin_url}", "artefact_id": "{artefact_id}", "resource_id": "{resource_id}", "media_type": "{media_type}"}'
```

Where:

* `{origin_url}` is the URL noted in step 7 (from SharePoint)
* `{artefact_id}` is the unique ID generated for the Artefact
* `{resource_id}` is the value of the `file_identifier` property in the metadata for the Artefact
* `{media_type}` is the (preferably [IANA assigned](https://www.iana.org/assignments/media-types/media-types.xhtml)) 
  media type for the Artefact

For example (based on [3]):

```shell
# with the awscurl installed and access to a AWS IAM principle with appropriate privileges
$ awscurl --region eu-west-1 --service lambda --access_key $AWS_ACCESS_KEY_ID --secret_key $AWS_SECRET_ACCESS_KEY 
'https://dvej4gdfa333uci4chyhkxj3wq0fkxrs.lambda-url.eu-west-1.on.aws/' --request POST --header 'Content-Type: application/json' --data $'{"artefact_id": "cb794264-e2d1-4a5a-8e31-8cf774fede54", "resource_id": "24dce09c-9eee-4d90-8402-63f63012d767", "media_type": "application/pdf", "origin_url": "https://nercacuk.sharepoint.com/sites/MAGICProductsDistribution/Main/24dce09c-9eee-4d90-8402-63f63012d767/foo-map.pdf"}'
```

[5]

```
https://data.bas.ac.uk/download/{artefact_id}
```

Where:

* `{artefact_id}` is the unique ID generated for the Artefact

For example (based on [4]):

```
https://data.bas.ac.uk/download/cb794264-e2d1-4a5a-8e31-8cf774fede54
```

## Implementation

This project consists of:

* a library and service for uploading and managing files within a SharePoint document library
* a workflow for depositing files described by a metadata record (see [Workflow](#workflow))
* a tool which automates this workflow based on a selected metadata record
* documentation for using this tool, including manual instructions for using the workflow if automated methods fail

### Workflow

For a metadata record from the [BAS Data Catalogue](https://gitlab.data.bas.ac.uk/MAGIC/add-metadata-toolbox/):

* deposit files in a SharePoint document library
* register download URLs for deposited files in the
  [Data Catalogue Downloads Proxy](https://gitlab.data.bas.ac.uk/MAGIC/add-metadata-toolbox/#downloads-proxy)
* updating the metadata record in the Data Catalogue (with links to deposited files via Downloads Proxy)

### Structure - conceptual

Conceptually, Artefacts (files) for Resources (products) are stored as immutable objects, with tags storing unique 
identifiers for each Artefact and the Resource they relate to.

For example, a map product ('Map of Foo') consists of two distribution files (Artefacts), a PDF and JPEG export.

* the identifier assigned to this product (Resource) is: `24dce09c-9eee-4d90-8402-63f63012d767`
* the identifier assigned to the PDF file (Artefact) is: `cb794264-e2d1-4a5a-8e31-8cf774fede54`
* the identifier assigned to the JPEG file (Artefact) is: `6c21b27a-154a-488c-9ff9-764e6e9441c0`

**Note:** The Resource identifier would be assigned when the metadata record for the Resource is created. Identifiers
for each Artefact would be assigned when they are deposited within this service.

Conceptually, these Artefacts would be stored as objects like this:

| Object Name    | Resource Identifier                    | Artefact Identifier                    |
| -------------- | -------------------------------------- | -------------------------------------- |
| `foo-map.pdf`  | `24dce09c-9eee-4d90-8402-63f63012d767` | `cb794264-e2d1-4a5a-8e31-8cf774fede54` |
| `foo-map.jpeg` | `24dce09c-9eee-4d90-8402-63f63012d767` | `6c21b27a-154a-488c-9ff9-764e6e9441c0` |

**Note:** Object names are not significant in this service or conceptual model, they could be anything.

**Note:** In cases where an Artefact needs to be changed (because the wrong file was selected, or contains a mistake 
for example), the correct file would need to deposited as a new Artefact, as Artefacts are immutable. Once added, the 
old artefact would be removed from the Resource (which are mutable).

### Structure - SharePoint

The conceptual structure above is implemented using SharePoint.

Artefacts are stored as files in a SharePoint document library. Files are grouped into directories named after the
Resource (product) they relate to. Two custom columns (`resource_id` and `artefact_id`), in the document library's
corresponding SharePoint list, are used to record the Resource and Artefact identifiers for each object/file.

**Note:** Files MAY be named, and renamed, using any naming scheme/convention. The `arefact_id` value MUST NOT be
changed.

**Note:** To facilitate automation, sub-directories within Resource directories MUST NOT be used.

The 'Map of Foo' example from earlier would therefore be stored like this:

```
MAGIC Products Distribution  <-- (SharePoint site)
└── Main  <-- (Document Library)
    └── 24dce09c-9eee-4d90-8402-63f63012d767  <-- (Directory for resource)
        | >> resource_id: '24dce09c-9eee-4d90-8402-63f63012d767'  <-- (Custom column for resource identifier)
        | >> artefact_id: '-'  <-- (Custom column for artefact identifier, not applicable for directories)
        ├── foo-map.pdf  <-- (Artefact for resource)
            | >> resource_id: '24dce09c-9eee-4d90-8402-63f63012d767'  <-- (Custom column for resource identifier)
            | >> artefact_id: 'cb794264-e2d1-4a5a-8e31-8cf774fede54'  <-- (Custom column for artefact identifier)
        └── foo-map.png  <-- (Artefact for resource)
            | >> resource_id: '24dce09c-9eee-4d90-8402-63f63012d767'  <-- (Custom column for resource identifier)
            | >> artefact_id: '6c21b27a-154a-488c-9ff9-764e6e9441c0'  <-- (Custom column for artefact identifier)
```

### Environments - conceptual

Different environments are used for different contexts/purposes.

Environments are isolated from each other, meaning Artefacts deposited in, or removed from, one environment will not
appear or disappear from other environments.

A single *production* environment is currently used. Others (such as training, testing) may be added in future.

### Environments - SharePoint

Different document libraries within the same overall SharePoint site are used for each environment.

| Document Library | Environment |
| ---------------- | ----------- |
| Main             | Production  |

### Permissions - Conceptual

Conceptually, permissions for Artefacts (files) are controlled by access and usage constraints applied to Resources
(products). This service is responsible for evaluating and enforcing these constraints.

**WARNING:** Constraints applied to Resources and their Artefacts can only be enforced at the point an Artefact is
accessed. Once downloaded, an authorised end-user could allow an unauthorised user to access their copy without any
permission checks, by emailing it to them for example.

Access constraints control who can access Resources. They fall into two categories:

* restricted - to a specified set of users
* unrestricted - accessible to anyone

**Note:** This service only supports *restricted* access constraints, see the [Limitations](#limitations) section
for more information.

Usage constraints control how, and under which conditions, Resources can be used. Typically these conditions are
within a standard or bespoke licence, which end-users may be required to agree to in order to use a Product.

**Note:** This service does not yet support usage constraints.

### Permissions - Metadata records

Access and usage constraints (described in the previous section) for Resources (products) are defined within ISO 19115
metadata. This service will use these constraints to apply suitable permissions to each Artefact within a Resource.

**Note:** The examples listed in this section use the JSON representation of the ISO 19139 (ISO 19115 XML encoding)
defined by the [BAS Metadata Library](https://gitlab.data.bas.ac.uk/uk-pdc/metadata-infrastructure/metadata-library),
which is typically used for authoring Resource metadata.

#### Access constraints

Access constraints are JSON objects with these properties and allowed values:

| Property                       | Type   | Required | Allowed Values                             |
|--------------------------------|--------|----------|--------------------------------------------|
| `type`                         | String | Yes      | 'access' [2]                               |
| `restriction_code`             | String | Yes      | 'restricted' [2]                           |
| `permissions`                  | Array  | Yes      | -                                          |
| `permissions.*`                | Object | Yes      | -                                          |
| `permissions.*.scheme`         | String | Yes      | 'ms_graph' [2]                             |
| `permissions.*.scheme_version` | String | Yes      | '1' [2]                                    |
| `permissions.*.directory_id`   | String | Yes      | 'b311db95-32ad-438f-a101-7ba061712a4e' [2] |
| `permissions.*.alias`          | Array  | No [1]   | -                                          |
| `permissions.*.alias.*`        | String | Yes      | '~nerc' [2]                                |
| `permissions.*.object_id`      | Array  | No [1]   | -                                          |
| `permissions.*.object_id.*`    | String | Yes      | Identifier for an object in the NERC AAD   |

[1] At least one of these properties MUST be specified.

[2] Required value. See the [Requirements](#requirements) section for more information.

For example:

```json
{
    "type": "access",
    "restriction_code": "restricted",
    "permissions": [
        {
            "scheme": "ms_graph",
            "scheme_version": "1",
            "directory_id": "b311db95-32ad-438f-a101-7ba061712a4e",
            "object_id": ["06fc160e-d099-4f5b-be19-edf662030ad5"]
        }
    ]
}
```

#### Constraints for products restricted to within NERC

Where a product is restricted, but can be accessed by anyone internally, it MUST be marked as restricted and specify a
conventional value `~nerc` to represent 'All NERC Staff'.

'All NERC Staff' in this context includes any user or service within the NERC Azure Active Directory, which includes
(but is not limited to):

* BAS staff (inc. students)
* BGS staff
* NERC staff
* various service accounts used for automated processes and tools

**WARNING:** To stress, 'All NERC Staff' is not limited to BAS but NERC generally.

Example access constraint:

```json
{
    "type": "access",
    "restriction_code": "restricted",
    "permissions": [
        {
            "scheme": "ms_graph",
            "scheme_version": "1",
            "directory_id": "b311db95-32ad-438f-a101-7ba061712a4e",
            "alias": ["~nerc"]
        }
    ]
}
```

#### Constraints for products restricted to members of a specific team

Where a product needs to be restricted to members of a specific team, or set of teams, it MUST be marked as restricted
and specify the identifier(s) for the Azure Active Directory group(s) that represent the relevant team(s) who's members
should have access.

In most cases, these groups will underpin the Microsoft Office 365 Team for that team, however any group can be used
(such as project specific group or a group representing something like the BAS Management Team). All members of
each group specified will be allowed access (i.e. a union of all group members).

Groups are referenced using their Object Identifier (Object ID), which can be found from the
[Groups section](https://portal.azure.com/#blade/Microsoft_AAD_IAM/GroupsManagementMenuBlade/AllGroups) of the Azure
Active Directory in the [Azure Portal](https://portal.azure.com).

For example, the group that underpins the Microsoft Office 365 Team for MAGIC is
[`25728084-25c1-459f-999e-d42720a5f8fa`](https://portal.azure.com/#blade/Microsoft_AAD_IAM/GroupDetailsMenuBlade/Overview/groupId/25728084-25c1-459f-999e-d42720a5f8fa).

Example access constraint (single team):

```json
{
    "type": "access",
    "restriction_code": "restricted",
    "permissions": [
        {
            "scheme": "ms_graph",
            "scheme_version": "1",
            "directory_id": "b311db95-32ad-438f-a101-7ba061712a4e",
            "object_id": ["25728084-25c1-459f-999e-d42720a5f8fa"]
        }
    ]
}
```

Example access constraint (multiple teams):

```json
{
    "type": "access",
    "restriction_code": "restricted",
    "permissions": [
        {
            "scheme": "ms_graph",
            "scheme_version": "1",
            "directory_id": "b311db95-32ad-438f-a101-7ba061712a4e",
            "object_id": ["25728084-25c1-459f-999e-d42720a5f8fa", "06fc160e-d099-4f5b-be19-edf662030ad5"]
        }
    ]
}
```

#### Constraints for products restricted to specific users

Where a product needs to be restricted to a specific user, or set of users, it MUST be marked as restricted and specify
the identifier(s) for the Azure Active Directory user(s) that should have access.

Users are referenced using their Object Identifier (Object ID), which can be found from the
[Users section](https://portal.azure.com/#view/Microsoft_AAD_IAM/UsersManagementMenuBlade/~/MsGraphUsers) of the Azure
Active Directory in the [Azure Portal](https://portal.azure.com).

For example, the Object ID for *Connie Watson* is `04615595-a264-4d8d-9a95-4b1ae6c8d85e`.

Example access constraint (single user):

```json
{
    "type": "access",
    "restriction_code": "restricted",
    "permissions": [
        {
            "scheme": "ms_graph",
            "scheme_version": "1",
            "directory_id": "b311db95-32ad-438f-a101-7ba061712a4e",
            "object_id": ["04615595-a264-4d8d-9a95-4b1ae6c8d85e"]
        }
    ]
}
```

Example access constraint (multiple users):

```json
{
    "type": "access",
    "restriction_code": "restricted",
    "permissions": [
        {
            "scheme": "ms_graph",
            "scheme_version": "1",
            "directory_id": "b311db95-32ad-438f-a101-7ba061712a4e",
            "object_id": ["04615595-a264-4d8d-9a95-4b1ae6c8d85e", "7aa5b9f2-25c1-4a88-8627-c0d7d1326b55"]
        }
    ]
}
```

### Permissions - SharePoint

Permissions described by metadata record access constraints are applied to items stored in SharePoint using the
Microsoft Graph API.

**Note:** Ad-hoc permission assignments MUST NOT be made directly within SharePoint. They may be removed or changed
without warning by this service.

Where permissions reference the `~nerc` 'All NERC Staff' alias, a view only 
[Organisational sharing link](https://docs.microsoft.com/en-us/graph/api/driveitem-createlink) is created for each
file (Artefact) associated with the Resource (product). These links will be used in distribution options, instead of
the normal item access URL.

Where permissions reference one or more Object IDs, one or more view only
[DriveRecipient](https://docs.microsoft.com/en-us/graph/api/resources/driverecipient) resources are
[created](https://docs.microsoft.com/en-us/graph/api/driveitem-invite), granting each permission to access the
directory representing the Resource (product). These permissions cascade to any files (Artefacts) within this directory.
Normal access URLs for each item/file are used in distribution options.

### SharePoint - objects reference

See the 
[MAGIC Products Distribution Service - Sharepoint objects reference](https://start.1password.com/open/i?a=QSB6V7TUNVEOPPPWR6G7S2ARJ4&v=ffy5l25mjdv577qj6izuk6lo4m&i=pnywcjeudvbo7beuw4om6jfpce&h=magic.1password.eu) 
item in the shared vault of the MAGIC 1Password account for the specific SharePoint resources used. Generic information 
is shown in this README.

**Note:** These resources are not secrets but are not listed publicly as a precaution.

#### SharePoint site

Graph resource reference: https://docs.microsoft.com/en-us/graph/api/resources/site

**Note:** To find the ID for this resource, query the
[search](https://docs.microsoft.com/en-us/graph/api/site-search) endpoint of the sites resource in Microsoft Graph,
e.g. `https://graph.microsoft.com/v1.0/sites?search=site_name`.

#### Document Library

Graph resource reference: https://docs.microsoft.com/en-us/graph/api/resources/drive

**Note:** To find the ID for this resource, query `https://graph.microsoft.com/v1.0/sites/{SITE}/drives`

#### Document Library items

Graph resource reference: 

To get details for an item in a Document Library, query: `https://graph.microsoft.com/v1.0/drives/{DRIVE}/items/{ITEM}`

To get permission details for an item in a Document Library, query:
`https://graph.microsoft.com/v1.0/drives/{DRIVE}/items/{ITEM}/permissions`

**Note:** To find the ID for this resource, query: 
`https://graph.microsoft.com/v1.0/drives/{DRIVE}/items/{ROOT ITEM}/children`

**Note:** To find the ID for this resource, query:
`https://graph.microsoft.com/v1.0/sites/{SITE}/drives/{DRIVE}/root`

#### Document Library List

Graph resource reference: https://docs.microsoft.com/en-us/graph/api/resources/list

**Note:** To find the ID for this resource, query `https://graph.microsoft.com/v1.0/sites/{SITE_ID}/lists`

## Setup

### Service Principles

Contact [BAS IT](mailto:servicedesk@bas.ac.uk) to request the creation of two service accounts/principles:

1. `basmagicanon_svcacc@bas.ac.uk` (BAS MAGIC Products Distribution - Anonymous Access Account)
1. `basmagiccond_svcacc@bas.ac.uk` (BAS MAGIC Products Distribution - Conditional Access Account)

**Note:** These accounts need to be propagated to Azure Active Directory, so they can use the Microsoft Graph API. 

See [#12](https://gitlab.data.bas.ac.uk/MAGIC/products-distribution/-/issues/12) and
[#18](https://gitlab.data.bas.ac.uk/MAGIC/products-distribution/-/issues/18) for example requests.

#### Priming service principles for non-interactive authentication

The non-interactive *Username and Password* (credentials) OAuth flow cannot be used for applications the user has not 
already consented to, as this requires an interactive session with a browser.

To provide this initial consent, the interactive *Device* flow can be used via the [Test Script](#test-script).

For each service principle:

1. generate a sign-in URL using the device OAuth flow [1]
2. sign-in with the email address for the service principle
3. agree to the scopes/permissions required by the application
4. complete the login in the application, which will retrieve an access token, confirming consent was successful

This only needs to be done once for each account.

[1]

```
$ poetry run python test-chain.py sign-in device
```

### SharePoint

Contact [BAS IT](mailto:servicedesk@bas.ac.uk) to request a new SharePoint site:

* name: `MAGICProductsDistribution`
* title: `MAGIC Products Distribution`
* type: *Team Site* (not *Communications Hub*)
* owners:
    * one or more admin accounts (e.g. `o365conwat@bas.ac.uk`), separate from end-user accounts
* members:
    * members of the [BAS MAGIC Team](https://nercacuk.sharepoint.com/sites/BASMagicTeam), as a group
* visitors: None

Once created, and as an admin user:

1. remove all widgets/text from the default site homepage
2. go to *Site contents* -> *Site settings* -> *Site permissions*
    * remove permissions for the 'MAGIC Products Distribution Visitors' group (which will remove the group)
3. go to *Site contents* -> *Site settings* -> *People and groups*
    * from the groups list in the left navigation pane, select *MAGIC Products Distribution Members*
    * choose *New* -> *Add Users*
    * invite the `basmagiccond_svcacc@bas.ac.uk` service principle
    * **DO NOT** add the `basmagicanon_svcacc@bas.ac.uk` service principle as a site member (or as any other role)
4. create a new document library:
    * name: `Main`
    * description: `Access copies of products created or managed by MAGIC for distribution. Production environment.`
    * 'show in site navigation': *False*
5. once created, add a new list column:
    * type: *Single line of text*
    * name: `resource_id`
    * description: `Resource identifier each artefact relates to`
    * default value: None
    * 'Use calculated value': *False*
    * (more options) maximum number of characters: `255`
    * (more options) 'Require that this column contains information': *True*
    * (more options) 'Enforce unique values': *False*
    * (more options) 'Add to all content types': *True*
    * (more options) column validation: None
6. once created, add a second new list column:
    * type: *Single line of text*
    * name: `artefact_id`
    * description: `Unique identifier for each resource artefact`
    * default value: None
    * 'Use calculated value': *False*
    * (more options) maximum number of characters: `255`
    * (more options) 'Require that this column contains information': *True*
    * (more options) 'Enforce unique values': *False*
    * (more options) 'Add to all content types': *True*
    * (more options) column validation: None

### Terraform

Terraform is used for registering an Azure Application Registration to allow this service to authenticate users and 
interact with SharePoint.

Access to the [BAS AWS account](https://gitlab.data.bas.ac.uk/WSF/bas-aws) 
(to access [Terraform remote state](#terraform-remote-state) state) and the NERC Azure tenancy are required to 
provision these resources.

```shell
$ cd provisioning/terraform
$ docker compose run terraform

$ az login --allow-no-subscriptions

$ terraform init
$ terraform validate
$ terraform fmt
$ terraform apply

$ exit
$ docker compose down
```

#### Terraform remote state

State information for this project is stored remotely using a
[Backend](https://www.terraform.io/docs/backends/index.html).

Specifically the [AWS S3](https://www.terraform.io/docs/backends/types/s3.html) backend as part of the
[BAS Terraform Remote State](https://gitlab.data.bas.ac.uk/WSF/terraform-remote-state) project.

Remote state storage will be automatically initialised when running `terraform init`. Any changes to remote state will
be automatically saved to the remote backend, there is no need to push or pull changes.

##### Remote state authentication

Permission to read and/or write remote state information for this project is restricted to authorised users. Contact
the [BAS Web & Applications Team](mailto:servicedesk@bas.ac.uk) to request access.

See the [BAS Terraform Remote State](https://gitlab.data.bas.ac.uk/WSF/terraform-remote-state) project for how these
permissions to remote state are enforced.

## Development

### Development environment

Git and [Poetry](https://python-poetry.org) are required to set up a local development environment of this project.

**Note:** If you use [Pyenv](https://github.com/pyenv/pyenv), this project sets a local Python version for consistency.

```shell
# clone from the BAS GitLab instance if possible
$ git clone https://gitlab.data.bas.ac.uk/MAGIC/products-distribution.git

# setup virtual environment
$ cd magic-products-distribution
$ poetry install
```

## Deployment

...

## Release procedure

...

## Feedback

The maintainer of this project is the BAS Mapping and Geographic Information Centre (MAGIC), they can be contacted at:
[magic@bas.ac.uk](mailto:magic@bas.ac.uk).

## Issue tracking

This project uses issue tracking, see the
[Issue tracker](https://gitlab.data.bas.ac.uk/MAGIC/products-distribution/-/issues) for more information.

**Note:** Read & write access to this issue tracker is restricted. Contact the project maintainer to request access.

## License

Copyright (c) 2022 UK Research and Innovation (UKRI), British Antarctic Survey.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
