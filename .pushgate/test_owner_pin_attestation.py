"""Rule tests use synthetic verifier output; real Sigstore proof is a hosted probe."""

import json
import unittest

from bootstrap_protocol import (
    PIN_CONTROLLER,
    PIN_MAIN,
    REPOSITORY,
    REPOSITORY_ID,
    digest,
)
from owner_pin_attestation import (
    ISSUER,
    PREDICATE,
    SIGNER_SHA,
    SIGNER_URI,
    validate_verified_pins,
)


class AttestedPinTests(unittest.TestCase):
    def fixture(self):
        context = {
            "GITHUB_REPOSITORY": REPOSITORY,
            "GITHUB_ACTIONS": "true",
            "CI": "true",
            "GITHUB_RUN_ID": "1",
            "GITHUB_RUN_ATTEMPT": "2",
            "GITHUB_SHA": "b" * 40,
            "GITHUB_REF": "refs/pull/11/merge",
        }
        run = {
            "id": 1,
            "run_attempt": 2,
            "head_sha": "a" * 40,
            "repository": {"id": REPOSITORY_ID, "full_name": REPOSITORY},
        }
        artifact = {
            "name": "baseline-owner-pins-1-2",
            "workflow_run": {"id": 1, "head_sha": "a" * 40},
        }
        pins = {PIN_MAIN: "c" * 40, PIN_CONTROLLER: "d" * 40}
        document = {
            "schema": 1,
            "repository": REPOSITORY,
            "repository_id": REPOSITORY_ID,
            "run_id": 1,
            "run_attempt": 2,
            "source_sha": "b" * 40,
            "source_ref": context["GITHUB_REF"],
            "pins": pins,
        }
        blob = json.dumps(document).encode()
        certificate = {
            "issuer": ISSUER,
            "subjectAlternativeName": SIGNER_URI,
            "buildSignerURI": SIGNER_URI,
            "buildSignerDigest": SIGNER_SHA,
            "runnerEnvironment": "github-hosted",
            "sourceRepositoryURI": "https://github.com/" + REPOSITORY,
            "sourceRepositoryIdentifier": str(REPOSITORY_ID),
            "sourceRepositoryDigest": "b" * 40,
            "sourceRepositoryRef": context["GITHUB_REF"],
            "runInvocationURI": f"https://github.com/{REPOSITORY}/actions/runs/1/attempts/2",
        }
        verified = [
            {
                "verificationResult": {
                    "signature": {"certificate": certificate},
                    "verifiedTimestamps": [{"type": "Tlog"}],
                    "statement": {
                        "_type": "https://in-toto.io/Statement/v1",
                        "predicateType": PREDICATE,
                        "subject": [
                            {"name": "pins.json", "digest": {"sha256": digest(blob)}}
                        ],
                    },
                }
            }
        ]
        return blob, verified, context, run, artifact, pins

    def test_verified_immutable_reader_and_pr_merge_identity(self):
        blob, verified, context, run, artifact, pins = self.fixture()
        self.assertEqual(
            validate_verified_pins(blob, verified, context, run, artifact), pins
        )

    def test_wrong_certified_identity_run_source_and_signer(self):
        for field in [
            "issuer",
            "subjectAlternativeName",
            "buildSignerURI",
            "buildSignerDigest",
            "runnerEnvironment",
            "sourceRepositoryURI",
            "sourceRepositoryIdentifier",
            "sourceRepositoryDigest",
            "sourceRepositoryRef",
            "runInvocationURI",
        ]:
            blob, verified, context, run, artifact, _ = self.fixture()
            verified[0]["verificationResult"]["signature"]["certificate"][field] = (
                "untrusted"
            )
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_verified_pins(blob, verified, context, run, artifact)

    def test_unsigned_altered_cross_run_and_wrong_artifact_fail(self):
        for failure in [
            "unsigned",
            "altered-pins",
            "missing-time",
            "wrong-subject",
            "wrong-predicate",
            "artifact-sha",
            "attempt",
            "document-source",
        ]:
            blob, verified, context, run, artifact, _ = self.fixture()
            if failure == "unsigned":
                verified = []
            elif failure in {"altered-pins", "document-source"}:
                document = json.loads(blob)
                if failure == "altered-pins":
                    document["pins"][PIN_MAIN] = "e" * 40
                else:
                    document["source_sha"] = "e" * 40
                blob = json.dumps(document).encode()
            elif failure == "missing-time":
                verified[0]["verificationResult"]["verifiedTimestamps"] = []
            elif failure == "wrong-subject":
                verified[0]["verificationResult"]["statement"]["subject"] = []
            elif failure == "wrong-predicate":
                verified[0]["verificationResult"]["statement"]["predicateType"] = (
                    "unsigned"
                )
            elif failure == "artifact-sha":
                artifact["workflow_run"]["head_sha"] = "e" * 40
            else:
                run["run_attempt"] = 3
            with self.subTest(failure=failure), self.assertRaises(ValueError):
                validate_verified_pins(blob, verified, context, run, artifact)


if __name__ == "__main__":
    unittest.main()
