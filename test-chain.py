import base64
import http.client
import sys
import json
import logging
from argparse import ArgumentParser
from typing import List, Dict, Optional
from pathlib import Path
from copy import deepcopy
from uuid import uuid4

import requests
import quickxorhash
from bas_metadata_library.standards.iso_19115_2 import MetadataRecordConfigV3 as MetadataRecordConfig
from bas_metadata_library.standards.iso_19115_common.utils import encode_config_for_json
from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate
from msal import PublicClientApplication
from requests import HTTPError
from requests_auth_aws_sigv4 import AWSSigV4

logging.basicConfig(level=logging.DEBUG)

parser = ArgumentParser(
    description="Test CLI for MAGIC Products Distribution Service",
    usage="""poetry python test-chain.py <command> [<args>]

The most commonly used commands are:
   sign-in     Sign into app using Azure AD account
   deposit     Deposit artefacts listed in a metadata record for a resource
""",
)
parser.add_argument("command", help="Subcommand to run")

schema_path = Path("./schema.json").resolve()

sharepoint_site_id: str = (
    "nercacuk.sharepoint.com,0561c437-744c-470a-887e-3d393e88e4d3,63825c43-db1b-40ca-a717-0365098c70c0"
)
sharepoint_drive_id: str = "b!N8RhBUx0CkeIfj05Pojk00NcgmMb28pApxcDZQmMcMBzlP8HkrS0TKveYyZFGRd3"
sharepoint_list_id: str = "07ff9473-b492-4cb4-abde-632645191777"

lookup_endpoint = "https://zrpqdlufnfqcmqmzppwzegosvu0rvbca.lambda-url.eu-west-1.on.aws/"
download_endpoint = "https://data.bas.ac.uk/download-testing"

auth_client_tenancy: str = "https://login.microsoftonline.com/b311db95-32ad-438f-a101-7ba061712a4e"
auth_client_id: str = "3b2c5acf-728a-4b78-85f0-9560a6aad701"
auth_client_scopes: List[str] = ["https://graph.microsoft.com/Files.ReadWrite.All"]
auth_token_path = Path("./auth-token.json")
auth_credentials_path = Path('./auth-credentials.json')


def save_auth_token(auth_payload):
    if 'error' in auth_payload.keys():
        print(auth_payload)
        raise RuntimeError("Error in Auth token")

    logging.debug(f"Saving auth payload to auth file at: '{auth_token_path.resolve()}'")
    with open(auth_token_path.resolve(), mode="w") as auth_token_file:
        json.dump(auth_payload, auth_token_file, indent=2)
    logging.info(f"Authentication token written to auth file at: '{auth_token_path.resolve()}'")


def auth_sign_in_credentials_flow() -> None:
    """
    Note warnings here: https://github.com/AzureAD/microsoft-authentication-library-for-python/wiki/Username-Password-Authentication
    """
    auth_client_public: PublicClientApplication = PublicClientApplication(
        client_id=auth_client_id, authority=auth_client_tenancy
    )

    logging.debug("Retrieving login credentials")
    with open(auth_credentials_path, mode='r') as credentials_file:
        credentials = json.load(credentials_file)

    logging.debug("Acquiring token from login credentials")
    auth_payload = auth_client_public.acquire_token_by_username_password(username=credentials['username'], password=credentials['password'], scopes=[])
    logging.debug(f"Auth payload:")
    logging.debug(auth_payload)
    save_auth_token(auth_payload=auth_payload)


def auth_sign_in_device_flow() -> None:
    auth_client_public: PublicClientApplication = PublicClientApplication(
        client_id=auth_client_id, authority=auth_client_tenancy
    )

    logging.debug("Generating device sign-in flow")
    auth_flow = auth_client_public.initiate_device_flow(scopes=auth_client_scopes)
    input(
        f"To sign-in, visit 'https://microsoft.com/devicelogin', enter this code '{auth_flow['user_code']}' and then press [enter] ..."
    )

    logging.info("Acquire auth token from Azure via completed auth flow")
    auth_payload = auth_client_public.acquire_token_by_device_flow(auth_flow)
    logging.debug(f"Auth payload:")
    logging.debug(auth_payload)
    save_auth_token(auth_payload=auth_payload)


def get_auth_token() -> str:
    logging.info(f"Loading auth token from auth file at: '{auth_token_path.resolve()}'")
    if not auth_token_path.resolve().exists():
        logging.error(f"Auth token file '{auth_token_path.resolve()}' does not exist")
        raise RuntimeError(f"Auth token file '{auth_token_path.resolve()}' does exist")
    with open(auth_token_path.resolve(), mode="r") as auth_file:
        auth_data = json.load(auth_file)
    try:
        logging.debug(f"Return auth token: '{auth_data['access_token']}'")
        return auth_data["access_token"]
    except KeyError:
        logging.error(f"Auth token file '{auth_token_path.resolve()}' does not contain 'access_token' property")
        raise RuntimeError(f"Auth token file '{auth_token_path.resolve()}' does not contain 'access_token' property")


def list_resources() -> List[str]:
    return ["ad042ccd-6967-4489-af35-07a49472362d"]


def print_resources() -> None:
    print("Available resources:")
    for resource_id in list_resources():
        print(f"* {resource_id}")


def get_record_path(resource_id: str) -> Path:
    if resource_id == "ad042ccd-6967-4489-af35-07a49472362d":
        return Path("./test-record.json").resolve()

    raise LookupError(f"File path mapping unavailable for resource '{resource_id}'")


def get_record_config(resource_id: str) -> MetadataRecordConfig:
    logging.info(f"Loading record for resource: {resource_id}")
    try:
        record_path = get_record_path(resource_id=resource_id)
        logging.debug(f"Record location matched to '{record_path}'")
    except LookupError as e:
        logging.error(f"Resource '{resource_id}' not mapped to record path")
        raise RuntimeError(e)

    record_config = MetadataRecordConfig()
    record_config.load(file=record_path)

    return record_config


def validate_record_config(record_config: MetadataRecordConfig) -> None:
    """
    Validate metadata record configuration for resource

    The record config will already be valid against the base schema for the record config class, this method checks the
    config is valid against the schema specific to this service too.
    """
    logging.debug("Encoding record config as JSON for validation")
    _config = encode_config_for_json(config=deepcopy(record_config.config))

    logging.debug("Loading service specific JSON Schema for validation")
    logging.debug(f"Service schema path: '{schema_path}'")
    with open(schema_path, mode="r") as schema_file:
        schema_data = json.load(schema_file)
    _schema = schema_data

    try:
        validate(instance=_config, schema=_schema)
    except ValidationError as e:
        logging.error(f"Record configuration not valid against service specific JSON Schema")
        raise RuntimeError("Record configuration not valid against service specific JSON Schema") from e


def save_record_config(record_config: MetadataRecordConfig) -> None:
    try:
        record_path = get_record_path(resource_id=record_config.config["file_identifier"])
        logging.debug(f"Record location matched to '{record_path}'")
    except LookupError as e:
        logging.error(f"Resource '{record_config.config['file_identifier']}' not mapped to record path")
        raise RuntimeError(e)

    logging.info(f"Saving record configuration to: '{record_path}'")
    record_config.dump(file=record_path)
    logging.debug(f"Re-saving record to fix JSON indenting issue in metadata library")
    with open(record_path, mode="r") as record_file:
        record_data = json.load(record_file)
    with open(record_path, mode="w") as record_file:
        json.dump(record_data, record_file, indent=2)


def hash_file_quickxor(file_path: Path) -> str:
    quickxor = quickxorhash.quickxorhash()
    quickxor_block_size = 2**20

    with open(file_path, mode="rb") as hash_file:
        while True:
            data = hash_file.read(quickxor_block_size)
            if not data:
                break
            quickxor.update(data)

    return base64.b64encode(quickxor.digest()).decode()


def get_sharepoint_directory(directory_name: Optional[str] = None, directory_id: Optional[str] = None) -> dict:
    logging.debug(f"directory name: '{directory_name}'")
    logging.debug(f"directory id: '{directory_id}'")

    if directory_name is not None and directory_id is not None:
        raise RuntimeError("Only one of 'directory_name' or 'directory_id' can be specified")
    if directory_name is not None:
        url = f"https://graph.microsoft.com/v1.0/drives/{sharepoint_drive_id}/root:/{directory_name}"
    if directory_id is not None:
        url = f"https://graph.microsoft.com/v1.0/drives/{sharepoint_drive_id}/items/{directory_id}"

    auth_token = get_auth_token()

    # noinspection PyUnboundLocalVariable
    directory_item = requests.get(url=url, headers={"Authorization": f"Bearer {auth_token}"})
    directory_item.raise_for_status()
    return directory_item.json()


def get_sharepoint_file(directory_id: str, file_name: Optional[str] = None, file_id: Optional[str] = None) -> dict:
    logging.debug(f"directory id: '{directory_id}'")
    logging.debug(f"file name: '{file_name}'")
    logging.debug(f"file id: '{file_id}'")

    if file_name is not None and file_id is not None:
        raise RuntimeError("Only one of 'directory_name' or 'directory_id' can be specified")
    if file_name is not None:
        url = f"https://graph.microsoft.com/v1.0/drives/{sharepoint_drive_id}/items/{directory_id}:/{file_name}:"
    if file_id is not None:
        url = f"https://graph.microsoft.com/v1.0/drives/{sharepoint_drive_id}/items/{file_id}"

    auth_token = get_auth_token()

    # noinspection PyUnboundLocalVariable
    directory_item = requests.get(url=url, headers={"Authorization": f"Bearer {auth_token}"})
    directory_item.raise_for_status()
    return directory_item.json()


def set_sharepoint_directory_metadata(directory_id: str, directory_metadata: Dict[str, str]) -> None:
    logging.debug(f"directory id: '{directory_id}'")
    logging.debug("Directory metadata:")
    logging.debug(directory_metadata)

    auth_token = get_auth_token()

    directory_list_item = requests.get(
        url=f"https://graph.microsoft.com/v1.0/drives/{sharepoint_drive_id}/items/{directory_id}/listitem",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    directory_list_item.raise_for_status()
    directory_list_item_data = directory_list_item.json()

    directory_list_item_fields = requests.patch(
        url=f"https://graph.microsoft.com/v1.0/sites/{sharepoint_site_id}/lists/{sharepoint_list_id}/items/{directory_list_item_data['id']}/fields",
        headers={"Authorization": f"Bearer {auth_token}"},
        json=directory_metadata,
    )
    directory_list_item_fields.raise_for_status()


def set_sharepoint_file_metadata(file_id: str, file_metadata: Dict[str, str]) -> None:
    logging.debug(f"file id: '{file_id}'")
    logging.debug("File metadata:")
    logging.debug(file_metadata)

    auth_token = get_auth_token()

    file_list_item = requests.get(
        url=f"https://graph.microsoft.com/v1.0/drives/{sharepoint_drive_id}/items/{file_id}/listitem",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    file_list_item.raise_for_status()
    file_list_item_data = file_list_item.json()

    file_list_item_fields = requests.patch(
        url=f"https://graph.microsoft.com/v1.0/sites/{sharepoint_site_id}/lists/{sharepoint_list_id}/items/{file_list_item_data['id']}/fields",
        headers={"Authorization": f"Bearer {auth_token}"},
        json=file_metadata,
    )
    file_list_item_fields.raise_for_status()


def create_sharepoint_directory(
    directory_name: str, directory_metadata: Dict[str, str], sharing_recipients: Optional[List[str]] = None
) -> None:
    logging.debug(f"Directory name: '{directory_name}'")
    logging.debug("Directory metadata:")
    logging.debug(directory_metadata)
    logging.debug(f"Sharing Recipients:")
    logging.debug(sharing_recipients)

    try:
        logging.info("Checking if directory already exists")
        get_sharepoint_directory(directory_name=directory_name)
        return None
    except HTTPError as e:
        if e.response.status_code != http.client.NOT_FOUND:
            logging.error("Cannot determine if SharePoint directory exists")
            raise RuntimeError("Cannot determine if SharePoint directory exists") from e

    try:
        logging.info("Creating directory")
        auth_token = get_auth_token()
        create_directory_item = requests.post(
            url=f"https://graph.microsoft.com/v1.0/drives/{sharepoint_drive_id}/root/children",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": directory_name,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "fail",
            },
        )
        create_directory_item.raise_for_status()
        create_directory_item_data = create_directory_item.json()
    except HTTPError as e:
        logging.error("Cannot create SharePoint directory")
        raise RuntimeError("Cannot create SharePoint directory") from e

    try:
        logging.info("Setting directory metadata")
        set_sharepoint_directory_metadata(
            directory_id=create_directory_item_data["id"], directory_metadata=directory_metadata
        )
    except HTTPError as e:
        logging.error("Cannot set SharePoint directory metadata")
        raise RuntimeError("Cannot set SharePoint directory metadata") from e

    if sharing_recipients is not None:
        logging.info("Setting directory permissions")

        logging.debug("Preparing recipients")
        _sharing_recipients = []
        for sharing_recipient in sharing_recipients:
            _sharing_recipients.append({"objectID": sharing_recipient})
        logging.debug("Prepared recipients:")
        logging.debug(_sharing_recipients)

        set_directory_permissions = requests.post(
            url=f"https://graph.microsoft.com/v1.0/drives/{sharepoint_drive_id}/items/{create_directory_item_data['id']}/invite",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "requireSignIn": True,
                "sendInvitation": False,
                "roles": ["read"],
                "recipients": _sharing_recipients,
            },
        )
        set_directory_permissions.raise_for_status()


def upload_sharepoint_file(
    file_path: Path, file_metadata: Dict[str, str], directory_id: str, sharing_link: bool = False
) -> Dict[str, str]:
    logging.debug(f"File path: '{file_path}'")
    logging.debug(f"File metadata:")
    logging.debug(file_metadata)
    logging.debug(f"Directory ID: '{directory_id}'")
    logging.debug(f"Sharing link: '{sharing_link}'")

    try:
        logging.info("Checking if file already exists")
        get_sharepoint_file(directory_id=directory_id, file_name=file_path.name)
    except HTTPError as e:
        if e.response.status_code != http.client.NOT_FOUND:
            logging.error("Cannot determine if SharePoint file exists")
            raise RuntimeError("Cannot determine if SharePoint file exists") from e

    try:
        logging.info("uploading file")
        auth_token = get_auth_token()

        # https://stackoverflow.com/a/60467652
        upload_session = requests.post(
            url=f"https://graph.microsoft.com/v1.0/drives/{sharepoint_drive_id}/items/{directory_id}:/{file_path.name}:/createUploadSession",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"@microsoft.graph.conflictBehavior": "fail"},
        )
        upload_session.raise_for_status()
        upload_session_data = upload_session.json()

        with open(file_path, "rb") as src_file:
            total_file_size = file_path.stat().st_size
            chunk_size = 327680  # set by Microsoft (≈4kB)
            chunks_count = total_file_size // chunk_size
            chunks_leftover = total_file_size - (chunk_size * chunks_count)

            # ensure there's at least one chunk for files under 320kB
            if chunks_count == 0:
                chunks_count = 1

            for chunk_index in range(0, chunks_count + 1):
                print(f"Processing chunk [{chunk_index}/{chunks_count}]", flush=True)

                chunk_data = src_file.read(chunk_size)
                if not chunk_data:
                    break

                # calculate range headers
                range_start = chunk_index * chunk_size
                range_end = range_start + chunk_size
                if (chunk_index == chunks_count) or (chunk_index == 0 and chunks_count == 1):
                    range_end = range_start + chunks_leftover
                print(f"bytes {range_start}-{range_end - 1}/{total_file_size}")
                headers = {
                    "Content-Length": str(chunk_size),
                    "Content-Range": f"bytes {range_start}-{range_end - 1}/{total_file_size}",
                }

                headers["Authorization"] = f"Bearer {auth_token}"
                chunk_upload = requests.put(
                    url=upload_session_data["uploadUrl"],
                    data=chunk_data,
                    headers=headers,
                )
                chunk_upload.raise_for_status()
        upload_item_data: dict = chunk_upload.json()
    except HTTPError as e:
        logging.error("Cannot upload SharePoint file")
        raise RuntimeError("Cannot upload SharePoint file") from e

    file_uri = upload_item_data["webUrl"]

    # verify hash
    if upload_item_data["file"]["hashes"]["quickXorHash"] != hash_file_quickxor(file_path=file_path):
        raise RuntimeError("Hash for uploaded file does not match file artefact")

    try:
        logging.info("Setting file metadata")
        set_sharepoint_file_metadata(file_id=upload_item_data["id"], file_metadata=file_metadata)
    except HTTPError as e:
        logging.error("Cannot set SharePoint directory metadata")
        raise RuntimeError("Cannot set SharePoint directory metadata") from e

    if sharing_link:
        logging.info("Creating organisation sharing link")
        share_link = requests.post(
            url=f"https://graph.microsoft.com/v1.0/drives/{sharepoint_drive_id}/items/{upload_item_data['id']}/createLink",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "type": "view",
                "scope": "organization",
            },
        )
        share_link.raise_for_status()
        share_link_data: dict = share_link.json()
        file_uri = share_link_data["link"]['webUrl']

    return {"file_uri": file_uri}


def get_resource_directory(resource_id: str) -> dict:
    logging.info(f"Getting information about resource directory for: '{resource_id}'")
    return get_sharepoint_directory(directory_name=resource_id)


def create_resource_directory(resource_id: str, constraint: dict) -> None:
    logging.info(f"Creating resource directory for: '{resource_id}'")
    logging.debug("Constraint:")
    logging.debug(constraint)

    recipients: Optional[List[Dict[str, str]]] = None
    if "object_id" in constraint["permissions"][0]:
        logging.debug("Processing permissions as sharing recipients")
        recipients = []
        for object_id in constraint["permissions"][0]["object_id"]:
            recipients.append({"objectID": object_id})

    create_sharepoint_directory(
        directory_name=resource_id,
        directory_metadata={"resource_id": resource_id, "artefact_id": "-"},
        sharing_recipients=recipients,
    )


def upload_resource_artefact(
    resource_id: str, resource_directory_id: str, constraint: dict, artefact: dict
) -> Dict[str, str]:
    logging.info(f"Uploading artefact for resource: '{resource_id}'")
    logging.debug(f"Resource directory ID: '{resource_directory_id}'")
    logging.debug(f"Constraint:")
    logging.debug(constraint)
    logging.debug(f"Artefact:")
    logging.debug(artefact)

    logging.info("Generating new artefact ID")
    artefact_id = str(uuid4())
    logging.debug(f"Artefact ID: {artefact_id}")

    logging.info("Preparing artefact path")
    artefact_uri: str = artefact["transfer_option"]["online_resource"]["href"]
    artefact_path = Path(artefact_uri.removeprefix("file://")).resolve()
    logging.debug(f"Artefact URI: {artefact_uri}")
    logging.debug(f"Artefact path: {artefact_path}")
    if not artefact_path.exists():
        logging.error(f"Artefact path '{artefact_path}' does not exist")
        raise RuntimeError(f"Artefact path '{artefact_path}' does not exist")

    logging.info("Preparing artefact permissions")
    sharing_link = False
    if "alias" in constraint["permissions"][0] and constraint["permissions"][0]["alias"] == ["~nerc"]:
        logging.debug("Enabling sharing link")
        sharing_link = True

    upload_data = upload_sharepoint_file(
        file_path=artefact_path,
        file_metadata={"resource_id": resource_id, "artefact_id": artefact_id},
        directory_id=resource_directory_id,
        sharing_link=sharing_link,
    )
    artefact_uri = upload_data["file_uri"]
    logging.info(f"Artefact URI: {artefact_uri}")

    return {"artefact_id": artefact_id, "artefact_uri": artefact_uri}


def determine_artefact_media_type(format_uri: str) -> str:
    logging.debug(f"Format URI: {format_uri}")
    if format_uri == "https://www.iana.org/assignments/media-types/application/pdf":
        return "application/pdf"
    elif format_uri == "https://www.iana.org/assignments/media-types/image/png":
        return "image/png"

    raise LookupError(f"Media type mapping unavailable for artefact format URI '{format_uri}'")


def create_artefact_lookup_item(resource_id: str, artefact_id: str, format_uri: str, origin_uri: str) -> None:
    logging.debug(f"Resource ID: {resource_id}")
    logging.debug(f"Artefact ID: {artefact_id}")
    logging.debug(f"Format URI: {format_uri}")
    logging.debug(f"Origin URI: {origin_uri}")

    logging.debug("determining media type for artefact")
    media_type = determine_artefact_media_type(format_uri=format_uri)
    logging.info(f"media type for item determined to be: '{media_type}'")

    logging.debug("Building artefact lookup item")
    lookup_item = {
        "resource_id": resource_id,
        "artefact_id": artefact_id,
        "media_type": media_type,
        "origin_uri": origin_uri,
    }
    logging.debug("Artefact lookup item:")
    logging.debug(lookup_item)

    deposit_request = requests.post(url=lookup_endpoint, json=lookup_item, auth=AWSSigV4("lambda"))
    deposit_request.raise_for_status()


def deposit_resource_artefact(resource_id: str, resource_directory_id: str, constraint: dict, artefact: dict) -> dict:
    logging.info(f"Depositing artefact for resource: '{resource_id}'")
    logging.debug(f"Resource directory ID: '{resource_directory_id}'")
    logging.debug(f"Constraint:")
    logging.debug(constraint)
    logging.debug(f"Artefact:")
    logging.debug(artefact)

    # Crude check for existing deposit
    logging.debug("Crudely checking if artefact already deposited")
    if download_endpoint in artefact["transfer_option"]["online_resource"]["href"]:
        artefact_id: str = str(artefact["transfer_option"]["online_resource"]["href"]).replace(
            f"{download_endpoint}/", ""
        )
        logging.info(f"Artefact already deposited with ID: '{artefact_id}'")
        return {"artefact_id": artefact_id, "artefact": artefact, "existing_deposit": True}

    upload_data = upload_resource_artefact(
        resource_id=resource_id, resource_directory_id=resource_directory_id, constraint=constraint, artefact=artefact
    )
    create_artefact_lookup_item(
        resource_id=resource_id,
        artefact_id=upload_data["artefact_id"],
        format_uri=artefact["format"]["href"],
        origin_uri=upload_data["artefact_uri"],
    )
    artefact["transfer_option"]["online_resource"]["href"] = f"{download_endpoint}/{upload_data['artefact_id']}"

    return {"artefact_id": upload_data["artefact_id"], "artefact": artefact, "existing_deposit": False}


def deposit_resource_artefacts(resource_id: str) -> dict:
    record_config = get_record_config(resource_id=resource_id)
    validate_record_config(record_config=record_config)

    deposit_data_ = {"artefacts": []}

    logging.info("processing constraints to apply to artefacts")
    constraint = record_config.config["identification"]["constraints"][0]
    logging.debug('Selected constraint:')
    logging.debug(constraint)

    logging.info("setting up directory for resource artefacts")
    create_resource_directory(resource_id=resource_id, constraint=constraint)
    resource_directory_id: str = get_resource_directory(resource_id=resource_id)["id"]

    logging.info("processing distribution options in resource")
    _distribution_options_count = len(record_config.config["distribution"])
    logging.debug(f"total distribution options: {_distribution_options_count}")
    for distribution_index, distribution_option in enumerate(record_config.config["distribution"]):
        logging.info(f"Processing distribution option [{distribution_index + 0}/{_distribution_options_count}]")
        logging.debug("Distribution option:")
        logging.debug(distribution_option)

        deposit_data = deposit_resource_artefact(
            resource_id=resource_id,
            resource_directory_id=resource_directory_id,
            constraint=constraint,
            artefact=distribution_option,
        )
        distribution_option = deposit_data["artefact"]
        logging.debug("Distribution option:")
        logging.debug(distribution_option)
        record_config.config["distribution"][distribution_index] = distribution_option
        deposit_data_["artefacts"].append(
            {"artefact_id": deposit_data["artefact_id"], "existing_deposit": deposit_data["existing_deposit"]}
        )

    validate_record_config(record_config=record_config)
    save_record_config(record_config=record_config)

    logging.debug("deposit data:")
    logging.debug(deposit_data_)
    return deposit_data_


if __name__ == "__main__":
    # specific arguments selected to ignore child command parameters
    args = parser.parse_args(sys.argv[1:2])

    if args.command == "sign-in":
        parser = ArgumentParser(description="Sign into app using Azure AD account")
        parser.add_argument(
            "flow", help="OAuth flow to use", choices=['device', 'credentials'], nargs="?", default='device'
        )
        # specific arguments selected to ignore parent command selection
        args = parser.parse_args(sys.argv[2:])

        if args.flow == 'device':
            auth_sign_in_device_flow()
        elif args.flow == 'credentials':
            auth_sign_in_credentials_flow()

        print("Ok. Signed in for next hour.")
        sys.exit(0)

    if args.command == "deposit":
        parser = ArgumentParser(description="Deposit artefacts listed in a metadata record for a resource")
        parser.add_argument(
            "resource_id", help="Resource identifier, omit to list available options", nargs="?", default=None
        )
        # specific arguments selected to ignore parent command selection
        args = parser.parse_args(sys.argv[2:])

        if args.resource_id is None:
            print_resources()
            sys.exit(0)

        print(f"Depositing artefacts for resource: '{args.resource_id}' ...")
        if args.resource_id not in list_resources():
            print(f"No. Unable to find resource '{args.resource_id}'")
            print("")
            print_resources()
            sys.exit(1)

        try:
            _deposit_data = deposit_resource_artefacts(resource_id=args.resource_id)
            print(f"OK. Artefacts for resource '{args.resource_id}' deposited.")
            print(_deposit_data)
            sys.exit(0)
        except RuntimeError as exception:
            print(f"No. {exception}.")
            print("")
            print("=== context ===")
            if hasattr(exception, "__cause__"):
                print(exception.__cause__)
            sys.exit(1)

    print("No. Unrecognised command, run with `--help` for available commands.")
    sys.exit(1)
