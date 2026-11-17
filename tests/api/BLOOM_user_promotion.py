"""
* @file     ${tests/api/BLOOM_user_promotion.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Only the initial administrator promotes users to admin; admins are never demoted.
* @author   Amine El Omari
* @date     2026-11-13
* @version  1.0.0
* @note     This module tests the user role route of the full app in-process.
"""

from tests.api.user_promotion import UserPromotionBase


class UserPromotionTest(UserPromotionBase):

    def setUpClass(self):
        super().setUpClass()
        bloom = self.bloom
        password = self.parameters.API_PASSWORD
        bloom.bloom_start_full_api()
        seed_email = bloom.bloom_seed_admin_email()
        bloom.bloom_add_admin(seed_email, password)
        self.seed, seed_login = bloom.bloom_log_in(seed_email, password)
        maintainer, other_admin, target, second_admin = self.parameters.PROMOTION_EMAILS
        roles = {
            maintainer: self.parameters.PROMOTION_MAINTAINER,
            other_admin: self.parameters.PROMOTION_ADMIN,
            target: self.parameters.PROMOTION_MAINTAINER,
            second_admin: self.parameters.PROMOTION_ADMIN,
        }
        created = {
            email: bloom.bloom_api_create_user(self.seed, email, password, role)
            for email, role in roles.items()
        }
        ids = {email: answer.json().get("id") for email, answer in created.items()}
        self.maintainer_id = ids[maintainer]
        self.target_id = ids[target]
        self.second_admin_id = ids[second_admin]
        self.other_admin, other_login = bloom.bloom_log_in(other_admin, password)
        self.sign_ins = [seed_login, other_login]
        self.created = [answer.status_code for answer in created.values()]

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    UserPromotionTest().run()
