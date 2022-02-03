import orjson
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from zerver.lib.actions import (
    do_change_realm_domain,
    do_change_user_role,
    do_create_realm,
    do_remove_realm_domain,
    do_set_realm_property,
)
from zerver.lib.domains import validate_domain
from zerver.lib.email_validation import email_allowed_for_realm
from zerver.lib.test_classes import ZulipTestCase
from zerver.models import DomainNotAllowedForRealmError, RealmDomain, UserProfile, get_realm


class RealmDomainTest(ZulipTestCase):
    def setUp(self) -> None:
        realm = get_realm("zulip")
        do_set_realm_property(realm, "emails_restricted_to_domains", True, acting_user=None)

    def test_list_realm_domains(self) -> None:
        self.login("iago")
        realm = get_realm("zulip")
        RealmDomain.objects.create(realm=realm, domain="acme.com", allow_subdomains=True)
        result = self.client_get("/json/realm/domains")
        self.assert_json_success(result)
        received = result.json()["domains"]
        expected = [
            {"domain": "zulip.com", "allow_subdomains": False},
            {"domain": "acme.com", "allow_subdomains": True},
        ]
        self.assertEqual(received, expected)

    def test_not_realm_admin(self) -> None:
        self.login("hamlet")
        result = self.client_post("/json/realm/domains")
        self.assert_json_error(result, "Must be an organization administrator")
        result = self.client_patch("/json/realm/domains/15")
        self.assert_json_error(result, "Must be an organization administrator")
        result = self.client_delete("/json/realm/domains/15")
        self.assert_json_error(result, "Must be an organization administrator")

    def test_create_realm_domain(self) -> None:
        self.login("iago")
        data = {
            "domain": "",
            "allow_subdomains": orjson.dumps(True).decode(),
        }
        result = self.client_post("/json/realm/domains", info=data)
        self.assert_json_error(result, "Invalid domain: Domain can't be empty.")

        data["domain"] = "acme.com"
        result = self.client_post("/json/realm/domains", info=data)
        self.assert_json_success(result)
        realm = get_realm("zulip")
        self.assertTrue(
            RealmDomain.objects.filter(
                realm=realm, domain="acme.com", allow_subdomains=True
            ).exists()
        )

        result = self.client_post("/json/realm/domains", info=data)
        self.assert_json_error(
            result, "The domain acme.com is already a part of your organization."
        )

        mit_user_profile = self.mit_user("sipbtest")
        self.login_user(mit_user_profile)

        do_change_user_role(
            mit_user_profile, UserProfile.ROLE_REALM_ADMINISTRATOR, acting_user=None
        )

        result = self.client_post(
            "/json/realm/domains", info=data, HTTP_HOST=mit_user_profile.realm.host
        )
        self.assert_json_success(result)

    def test_patch_realm_domain(self) -> None:
        self.login("iago")
        realm = get_realm("zulip")
        RealmDomain.objects.create(realm=realm, domain="acme.com", allow_subdomains=False)
        data = {
            "allow_subdomains": orjson.dumps(True).decode(),
        }
        url = "/json/realm/domains/acme.com"
        result = self.client_patch(url, data)
        self.assert_json_success(result)
        self.assertTrue(
            RealmDomain.objects.filter(
                realm=realm, domain="acme.com", allow_subdomains=True
            ).exists()
        )

        url = "/json/realm/domains/non-existent.com"
        result = self.client_patch(url, data)
        self.assertEqual(result.status_code, 400)
        self.assert_json_error(result, "No entry found for domain non-existent.com.")

    def test_delete_realm_domain(self) -> None:
        self.login("iago")
        realm = get_realm("zulip")
        RealmDomain.objects.create(realm=realm, domain="acme.com")
        result = self.client_delete("/json/realm/domains/non-existent.com")
        self.assertEqual(result.status_code, 400)
        self.assert_json_error(result, "No entry found for domain non-existent.com.")

        result = self.client_delete("/json/realm/domains/acme.com")
        self.assert_json_success(result)
        self.assertFalse(RealmDomain.objects.filter(domain="acme.com").exists())
        self.assertTrue(realm.emails_restricted_to_domains)

    def test_delete_all_realm_domains(self) -> None:
        self.login("iago")
        realm = get_realm("zulip")
        query = RealmDomain.objects.filter(realm=realm)

        self.assertTrue(realm.emails_restricted_to_domains)
        for realm_domain in query.all():
            do_remove_realm_domain(realm_domain, acting_user=None)
        self.assertEqual(query.count(), 0)
        # Deleting last realm_domain should set `emails_restricted_to_domains` to False.
        # This should be tested on a fresh instance, since the cached objects
        # would not be updated.
        self.assertFalse(get_realm("zulip").emails_restricted_to_domains)

    def test_email_allowed_for_realm(self) -> None:
        realm1 = do_create_realm("testrealm1", "Test Realm 1", emails_restricted_to_domains=True)
        realm2 = do_create_realm("testrealm2", "Test Realm 2", emails_restricted_to_domains=True)

        realm_domain = RealmDomain.objects.create(
            realm=realm1, domain="test1.com", allow_subdomains=False
        )
        RealmDomain.objects.create(realm=realm2, domain="test2.test1.com", allow_subdomains=True)

        email_allowed_for_realm("user@test1.com", realm1)
        with self.assertRaises(DomainNotAllowedForRealmError):
            email_allowed_for_realm("user@test2.test1.com", realm1)
        email_allowed_for_realm("user@test2.test1.com", realm2)
        email_allowed_for_realm("user@test3.test2.test1.com", realm2)
        with self.assertRaises(DomainNotAllowedForRealmError):
            email_allowed_for_realm("user@test3.test1.com", realm2)

        do_change_realm_domain(realm_domain, True)
        email_allowed_for_realm("user@test1.com", realm1)
        email_allowed_for_realm("user@test2.test1.com", realm1)
        with self.assertRaises(DomainNotAllowedForRealmError):
            email_allowed_for_realm("user@test2.com", realm1)

    def test_realm_realm_domains_uniqueness(self) -> None:
        realm = get_realm("zulip")
        with self.assertRaises(IntegrityError):
            RealmDomain.objects.create(realm=realm, domain="zulip.com", allow_subdomains=True)

    def test_validate_domain(self) -> None:
        invalid_domains = [
            "",
            "test",
            "t.",
            "test.",
            ".com",
            "-test",
            "test...com",
            "test-",
            "test_domain.com",
            "test.-domain.com",
            "a" * 255 + ".com",
        ]
        for domain in invalid_domains:
            with self.assertRaises(ValidationError):
                validate_domain(domain)

        valid_domains = ["acme.com", "x-x.y.3.z"]
        for domain in valid_domains:
            validate_domain(domain)