Feature: User Authentication
  As a registered user
  I want to log in to the SauceDemo portal
  So that I can view the inventory catalog

  Scenario: Successful login with standard credentials
    Given Navigate to https://www.saucedemo.com
    When Enter username standard_user
    And Enter password secret_sauce
    And Click Login button
    Then Verify main page content visible
