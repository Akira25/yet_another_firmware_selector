#!/usr/bin/env python3
"""
Tool to create overview.json files and update the config.js.
"""

from pathlib import Path
import urllib.request
import tempfile
import argparse
import json
import glob
import sys
import os
import re

SUPPORTED_METADATA_VERSION = 1

assert sys.version_info >= (3, 5), "Python version too old. Python >=3.5.0 needed."


# accepts {<file-path>: <file-content>}
def merge_profiles(profiles, download_url):
    # json output data
    output = {}

    def get_title(title):
        if "title" in title:
            return title["title"]
        else:
            return "{} {} {}".format(
                title.get("vendor", ""), title["model"], title.get("variant", "")
            ).strip()

    def add_profile(path, id, target, profile, code=None):
        images = []
        for image in profile["images"]:
            images.append({"name": image["name"], "type": image["type"]})

        if target is None:
            target = profile["target"]

        for entry in profile["titles"]:
            title = get_title(entry)

            if len(title) == 0:
                sys.stderr.write(
                    "Empty title. Skip title for {} in {}\n".format(id, path)
                )
                continue

            output["models"][title] = {"id": id, "target": target, "images": images}

            if code is not None:
                output["models"][title]["code"] = code

    for path, content in profiles.items():
        obj = json.loads(content.decode("utf-8"))

        if obj["metadata_version"] != SUPPORTED_METADATA_VERSION:
            sys.stderr.write(
                "{} has unsupported metadata version: {} => skip\n".format(
                    path, obj["metadata_version"]
                )
            )
            continue

        code = obj.get("version_code", obj.get("version_commit"))

        if "version_code" not in output:
            output = {"version_code": code, "download_url": download_url, "models": {}}

        # if we have mixed codes/commits, store in device object
        if output["version_code"] == code:
            code = None

        try:
            if "profiles" in obj:
                for id in obj["profiles"]:
                    add_profile(path, id, obj.get("target"), obj["profiles"][id], code)
            else:
                add_profile(path, obj["id"], obj["target"], obj, code)
        except json.decoder.JSONDecodeError as e:
            sys.stderr.write("Skip {}\n   {}\n".format(path, e))
        except KeyError as e:
            sys.stderr.write("Abort on {}\n   Missing key {}\n".format(path, e))
            exit(1)

    return output


def update_config(config_path, versions):
    content = ""
    with open(config_path, "r") as file:
        content = file.read()

    content = re.sub("versions:[\\s]*{[^}]*}", "versions: {}".format(versions), content)
    with open(config_path, "w+") as file:
        file.write(content)


"""
Scrape profiles.json using links like https://downloads.openwrt.org/releases/19.07.3/targets/?json
Merge into overview.json files.
Update config.json.
"""


def scrape(args):
    url = args.domain
    www_path = args.www_path
    config_path = "{}/config.js".format(www_path)
    data_path = "{}/data".format(www_path)
    versions = {}

    def handle_release(target):
        profiles = {}
        with urllib.request.urlopen("{}/?json".format(target)) as file:
            array = json.loads(file.read().decode("utf-8"))
            for profile in filter(lambda x: x.endswith("/profiles.json"), array):
                with urllib.request.urlopen("{}/{}".format(target, profile)) as file:
                    profiles["{}/{}".format(target, profile)] = file.read()
        return profiles

    if not os.path.isfile(config_path):
        print("file not found: {}".format(config_path))
        exit(1)

    # fetch release URLs
    with urllib.request.urlopen(url) as infile:
        for path in re.findall(r"href=[\"']?([^'\" >]+)", str(infile.read())):
            if not path.startswith("/") and path.endswith("targets/"):
                release = path.strip("/").split("/")[-2]
                download_url = "{}/{}/{{target}}".format(url, path)

                profiles = handle_release("{}/{}".format(url, path))
                output = merge_profiles(profiles, download_url)
                if len(output) > 0:
                    os.makedirs("{}/{}".format(data_path, release), exist_ok=True)
                    # write overview.json
                    with open(
                        "{}/{}/overview.json".format(data_path, release), "w"
                    ) as outfile:
                        if args.formatted:
                            json.dump(output, outfile, indent="  ", sort_keys=True)
                        else:
                            json.dump(output, outfile, sort_keys=True)

                    versions[release] = "data/{}/overview.json".format(release)

    update_config(config_path, versions)


"""
Scrape profiles.json using wget (slower but more generic).
Merge into overview.json files.
Update config.json.
"""


def scrape_wget(args):
    url = args.domain
    www_path = args.www_path
    config_path = "{}/config.js".format(www_path)
    data_path = "{}/data".format(www_path)
    versions = {}

    with tempfile.TemporaryDirectory() as tmp_dir:
        # download all profiles.json files
        os.system(
            "wget -c -r -P {} -A 'profiles.json' --reject-regex 'kmods|packages' --no-parent {}".format(
                tmp_dir, url
            )
        )

        # delete empty folders
        os.system("find {}/* -type d -empty -delete".format(tmp_dir))

        # create overview.json files
        for path in glob.glob("{}/*/snapshots".format(tmp_dir)) + glob.glob(
            "{}/*/releases/*".format(tmp_dir)
        ):
            release = os.path.basename(path)
            base = path[len(tmp_dir) + 1 :]

            profiles = {}
            for ppath in Path(path).rglob("profiles.json"):
                with open(ppath, "r") as file:
                    profiles[ppath] = file.read()

            if len(profiles) == 0:
                continue

            versions[release] = "data/{}/overview.json".format(release)

            output = merge_profiles(
                profiles, "https://{}/targets/{{target}}".format(base)
            )
            os.makedirs("{}/{}".format(data_path, release), exist_ok=True)

            # write overview.json
            with open("{}/{}/overview.json".format(data_path, release), "w") as outfile:
                if args.formatted:
                    json.dump(output, outfile, indent="  ", sort_keys=True)
                else:
                    json.dump(output, outfile, sort_keys=True)

        update_config(config_path, versions)


"""
Find and merge json files for a single release.
"""


def merge(args):
    input_paths = args.input_path
    # OpenWrt JSON device files
    profiles = {}

    def add_path(path):
        with open(path, "r") as file:
            profiles[path] = file.read()

    for path in input_paths:
        if os.path.isdir(path):
            for filepath in Path(path).rglob("*.json"):
                add_path(filepath)
        else:
            if not path.endswith(".json"):
                sys.stderr.write("Folder does not exists: {}\n".format(path))
                exit(1)
            add_path(path)

    output = merge_profiles(profiles, args.download_url)

    if args.formatted:
        json.dump(output, sys.stdout, indent="  ", sort_keys=True)
    else:
        json.dump(output, sys.stdout, sort_keys=True)


"""
Scan local directory for releases with profiles.json.
Merge into overview.json files.
Update config.json.
"""


def scan(args):
    # firmware selector config
    config_path = "{}/config.js".format(args.www_path)
    # the overview.json files are placed here
    data_path = "{}/data".format(args.www_path)
    versions = {}

    # args.images_path => args.releases_path
    releases = {}
    for path in Path(args.images_path).rglob("profiles.json"):
        with open(path, "rb") as file:
            content = file.read()
            obj = json.loads(content)
            release = obj["version_number"]
            releases.setdefault(release, {})[path] = content

    for release, profiles in releases.items():
        output = merge_profiles(profiles, args.download_url)

        versions[release] = "data/{}/overview.json".format(release)
        os.makedirs("{}/{}".format(data_path, release), exist_ok=True)

        # write overview.json
        with open("{}/{}/overview.json".format(data_path, release), "w") as outfile:
            if args.formatted:
                json.dump(output, outfile, indent="  ", sort_keys=True)
            else:
                json.dump(output, outfile, sort_keys=True)

    update_config(config_path, versions)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--formatted", action="store_true", help="Output formatted JSON data."
    )
    subparsers = parser.add_subparsers(dest="action")
    subparsers.required = True

    parser_merge = subparsers.add_parser(
        "merge", help="Search for profiles.json files and output an overview.json."
    )
    parser_merge.add_argument(
        "input_path",
        nargs="+",
        help="Input folder that is traversed for OpenWrt JSON device files.",
    )
    parser_merge.add_argument(
        "--download-url",
        action="store",
        default="",
        help="Link to get the image from. May contain {target} (replaced by e.g. ath79/generic), {version} (replace by the version key from config.js) and {commit} (git commit in hex notation).",
    )

    parser_scrape = subparsers.add_parser("scrape", help="Scrape webpage for releases.")
    parser_scrape.add_argument(
        "domain", help="Domain to scrape. E.g. https://downloads.openwrt.org"
    )
    parser_scrape.add_argument("www_path", help="Path the config.js file is in.")
    parser_scrape.add_argument(
        "--use-wget", action="store_true", help="Use wget to scrape the site."
    )

    parser_scan = subparsers.add_parser("scan", help="Scan directory for releases.")
    parser_scan.add_argument(
        "download_url", help="Download for images. E.g. https://downloads.openwrt.org"
    )
    parser_scan.add_argument("images_path", help="Directory to scan for releases.")
    parser_scan.add_argument("www_path", help="Path the config.js file is in.")

    args = parser.parse_args()

    if args.action == "merge":
        merge(args)

    if args.action == "scan":
        scan(args)

    if args.action == "scrape":
        if args.use_wget:
            scrape_wget(args)
        else:
            scrape(args)


if __name__ == "__main__":
    main()
