"""Facebook DOM selectors. Isolated here because FB changes them often.

If scanning breaks, update these first. Last verified: 2026-05-11
"""

POST_ARTICLE = '[role="feed"] [role="article"]'
POST_PERMALINK = 'a[href*="/groups/"][href*="/posts/"], a[href*="/groups/"][href*="/permalink/"]'
POST_AUTHOR_NAME = 'strong span, h3 span'
POST_AUTHOR_LINK = 'a[href*="/user/"]'
POST_TIMESTAMP = 'a[href*="/posts/"] span[id], a[href*="/permalink/"] span[id]'
POST_TEXT_CONTAINER = '[data-ad-comet-preview="message"], [data-ad-preview="message"]'
POST_PHOTO_IMG = 'img[data-visualcompletion="media-vc-image"]'
POST_SEE_MORE_BUTTON = 'div[role="button"]:has-text("See more"), div[role="button"]:has-text("Daugiau"), div[role="button"]:has-text("Ещё")'

LOGIN_FORM_INPUT = 'input[name="email"]'
LOGIN_PROFILE_INDICATOR = '[aria-label="Your profile"], [role="banner"] [role="navigation"]'

GROUP_URL_TEMPLATE = "https://www.facebook.com/groups/{group_id}"
