// The words of the Biller Groups report. Everything else comes from the recorded takes.
module.exports = {
  title: 'Biller Groups: the feature, working',
  slides: [
    {
      title: 'What you need to know',
      html: `<h1>{{HEADLINE}}</h1>
{{FAILED}}
<div class="box warn"><h2>One thing to check: limited users on dev</h2>
<p>A person limited to some billers only stays limited if core's database user is not a superuser. That was not checked on dev or prod. If it is a superuser, limited users there see every biller.</p>
<p><b>To check:</b> on dev, sign in as a Biller level user and open Insights. It should list only their billers.</p></div>
<div class="box"><h2>One decision for you</h2>
<p>A group draft reopened in a fresh tab loses the group's branding. The request stays attributed to the group. The loan response has no group field, so the fix needs a BE change. Leave it or ask for one.</p></div>
<div class="box"><h2>Small things, no action needed</h2><ul>
<li>On a biller's page, the logo preview shows a LOGO placeholder while the text says it uses the group's logo. The app does show the group's logo. Found while recording, not fixed.</li>
<li>A person limited in one group and unlimited in another gets a 403 on the second group's biller. BE limit.</li>
</ul></div>`,
    },
    {
      title: 'How the 3 connect',
      html: `<h1>What you set in the Admin Portal decides the other two</h1>
<table><tr><th>In the Admin Portal</th><th>Borrower app</th><th>Biller Portal</th></tr>
<tr><td>Biller turned on</td><td>Listed in the group's search</td><td>Live on Bank Details</td></tr>
<tr><td>Biller left off</td><td>Not listed. Its link goes to the group's link.</td><td>Still in the filter, marked Not live on Bank Details</td></tr>
<tr><td>Slug</td><td>Its own link, straight to that biller</td><td></td></tr>
<tr><td>Display name and logo</td><td>Landing page and flow. With none set, the group's are used.</td><td>Display name in the filter</td></tr>
<tr><td>Invite at Biller level</td><td></td><td>That person sees only those billers</td></tr></table>
<h2>What this was recorded on</h2>
<p><b>Not the dev environment.</b> Local zng-api and a local database, with a test group, "Cedar Valley Utilities", made for this. All names and amounts are test data. Release web builds: zng-admin <code>6a31bd2</code>, zng-biller built today at 17:54, and zng-app built at 01:16, before commits <code>5251b221</code> (draft resume) and <code>948a84e3</code> (all billers off), neither of which this recording covers.</p>
<p>Core's database user was switched to a non-superuser for the recordings, so limits applied, and has been switched back.</p>
<h2>What Claude added to the recordings</h2>
<p>The red dot, the captions and the voice. The voice is a local model reading the captions, so it can mispronounce a name. Page loads are cut, and video runs at normal speed: the player has a speed button. The script signs people in directly, so no invite email or login screen is shown.</p>
<h2>Not shown</h2>
<ul><li>Saving a real bank account: there's no SVB key locally, so the form opens but isn't saved.</li>
<li>Custom landing pages, phone size, and a request or signup being attributed to the group.</li></ul>`,
    },
    {
      title: 'Admin Portal',
      clip: 'ap',
      takes: ['ap'],
      html: `<h1>Admin Portal: <a href="https://app.shortcut.com/zirtue/story/56607">sc-56607</a></h1>
<p>Attached billers became a table, each biller got its own page, and invites got an access level. Billers start off, so nothing reaches borrowers until an admin turns it on.</p>
<p class="note">Click the video to pause. Click a step to jump to it.</p>`,
    },
    {
      title: 'Borrower app',
      clip: 'app',
      takes: ['app'],
      html: `<h1>Borrower app: <a href="https://app.shortcut.com/zirtue/story/56595">sc-56595</a>, <a href="https://app.shortcut.com/zirtue/story/56605">sc-56605</a></h1>
<p>A group's link now lets the borrower pick their biller. A biller's own link skips that step. Uses the billers set up in the previous recording.</p>`,
    },
    {
      title: 'Biller Portal',
      clip: 'bp',
      takes: ['bp-ava', 'bp-dana', 'bp-mia'],
      html: `<h1>Biller Portal: <a href="https://app.shortcut.com/zirtue/story/56606">sc-56606</a>, <a href="https://app.shortcut.com/zirtue/story/56468">sc-56468</a></h1>
<p>Numbers can narrow to one biller, access can be limited to some billers, and Bank Details and the Insights ACH view are new. Dana is the person invited in the Admin Portal recording.</p>`,
    },
    {
      title: 'Do it yourself',
      html: `<h1>Do it yourself</h1>
<div class="box"><h2>1. Admin Portal: B/P Toolkit, open a published group</h2><ol>
<li>Click a biller's name, then flip its switch on. Or use Turn on in the table.</li>
<li>Type a Display name and a Slug, then Save changes.</li>
<li>Upload a logo and press the Save beside it. Do this after step 2: Save changes refuses while a logo is waiting.</li>
<li>Back on the group, press Invite teammate. Fill in the name and email, pick Biller level, tick the billers, Send invite.</li>
</ol></div>
<div class="box"><h2>2. Borrower app: open these links</h2><ol>
<li><code>/biller/&lt;group slug&gt;</code>, Pay my bill, enter an account number, tap the search.</li>
<li><code>/biller/&lt;biller slug&gt;</code>, Pay my bill, enter an account number.</li>
<li>The link of a biller you turned off. The address changes to the group's link.</li>
</ol></div>
<div class="box"><h2>3. Biller Portal: sign in as the person you invited</h2><ol>
<li>Dev is <code>biller.dev.zirtue.com</code>, and the code on dev is <code>000000</code>.</li>
<li>Overview: open the filter, pick a biller, compare the cards.</li>
<li>Insights: filter, click a row, Export as .csv.</li>
<li>Team: check the Billers column. Bank Details: check it lists only their billers.</li>
</ol></div>
<p class="note">Skip non-RPPS bank account steps for now: non-RPPS billers aren't supported yet.</p>`,
    },
  ],
};
