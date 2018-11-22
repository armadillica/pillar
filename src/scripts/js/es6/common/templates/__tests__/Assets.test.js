import { Assets } from '../nodes/Assets'

jest.useFakeTimers();

describe('Assets', () => {
    describe('create$listItem', () => {
        let nodeDoc;
        let spyGet;
        beforeEach(()=>{
            // mock now to get a stable pretty printed created
            Date.now = jest.fn(() => new Date(Date.UTC(2018,
                10, //November! zero based month!
                28, 11, 46, 30)).valueOf()); // A Tuesday

            nodeDoc = {
                _id: 'my-asset-id',
                name: 'My Asset',
                node_type: 'asset',
                _created: "Wed, 07 Nov 2018 16:35:09 GMT",
                project: {
                    name: 'My Project',
                    url: 'url-to-project'
                },
                properties: {
                    content_type: 'image'
                }
            };

            spyGet = spyOn($, 'get').and.callFake(function(url) {
                let ajaxMock = $.Deferred();
                let response = {
                    variations: [{
                        size: 'l',
                        link: 'wrong-img-link',
                        width: 150,
                        height: 170,
                    },{
                        size: 'm',
                        link: 'img-link',
                        width: 50,
                        height: 70,
                    },{
                        size: 's',
                        link: 'wrong-img-link',
                        width: 5,
                        height: 7,
                    }]
                }
                ajaxMock.resolve(response);
                return ajaxMock.promise();
            });
        });
        describe('image content', () => {
            test('node with picture', done => {
                nodeDoc.picture = 'picture_id';
                let $card = Assets.create$listItem(nodeDoc);
                jest.runAllTimers();
                expect($card.length).toEqual(1);
                expect($card.prop('tagName')).toEqual('A'); // <a>
                expect($card.hasClass('asset')).toBeTruthy();
                expect($card.hasClass('card')).toBeTruthy();
                expect($card.attr('href')).toEqual('/nodes/my-asset-id/redir');
                expect($card.attr('title')).toEqual('My Asset');
    
                let $body = $card.find('.card-body');
                expect($body.length).toEqual(1);
    
                let $title = $body.find('.card-title');
                expect($title.length).toEqual(1);
                
                expect(spyGet).toHaveBeenCalledTimes(1);
                expect(spyGet).toHaveBeenLastCalledWith('/api/files/picture_id');

                let $image = $card.find('img');
                expect($image.length).toEqual(1);

                let $imageSubsititure = $card.find('.pi-asset');
                expect($imageSubsititure.length).toEqual(0);
    
                let $progress = $card.find('.progress');
                expect($progress.length).toEqual(0);

                let $watched = $card.find('.card-label');
                expect($watched.length).toEqual(0);

                expect($card.find(':contains(3 weeks ago)').length).toBeTruthy();
                done();
            });

            test('node without picture', done => {
                let $card = Assets.create$listItem(nodeDoc);
                expect($card.length).toEqual(1);
                expect($card.prop('tagName')).toEqual('A'); // <a>
                expect($card.hasClass('asset')).toBeTruthy();
                expect($card.hasClass('card')).toBeTruthy();
                expect($card.attr('href')).toEqual('/nodes/my-asset-id/redir');
                expect($card.attr('title')).toEqual('My Asset');
    
                let $body = $card.find('.card-body');
                expect($body.length).toEqual(1);
    
                let $title = $body.find('.card-title');
                expect($title.length).toEqual(1);

                expect(spyGet).toHaveBeenCalledTimes(0);

                let $image = $card.find('img');
                expect($image.length).toEqual(0);

                let $imageSubsititure = $card.find('.pi-asset');
                expect($imageSubsititure.length).toEqual(1);
    
                let $progress = $card.find('.progress');
                expect($progress.length).toEqual(0);

                let $watched = $card.find('.card-label');
                expect($watched.length).toEqual(0);
                
                expect($card.find(':contains(3 weeks ago)').length).toBeTruthy();
                done();
            });
        });
    })
});
